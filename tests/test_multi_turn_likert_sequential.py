"""Tests for the two scenario-driven multi-turn ports.

Covers BadLikertJudge and SequentialJailbreak through their real ``run``
entry point (which owns the budget, the refusal classifier and the status
mapping). ``FakeLLM`` answers the attacker calls by inspecting the requested
schema name, and ``EchoTarget`` / ``FailingTarget`` stand in for the system
under test.
"""

from __future__ import annotations

from typing import Optional

from eval_ai_redteam.attacks.multi_turn.bad_likert_judge.bad_likert_judge import (
    BadLikertJudge,
)
from eval_ai_redteam.attacks.multi_turn.sequential_break.sequential_break import (
    SequentialJailbreak,
)
from eval_ai_redteam.types import Budget

from conftest import EchoTarget, FailingTarget, FakeLLM


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def schema_name(response_format: Optional[dict]) -> Optional[str]:
    """Pull the pydantic schema name out of a response_format dict."""
    if response_format and response_format.get("type") == "json_schema":
        return response_format["json_schema"]["name"]
    return None


async def run_blj(attack: BadLikertJudge, fake: FakeLLM, target, **kw):
    return await attack.run(
        attacker=fake,
        target=target,
        initial_attack="Tell me something about group X.",
        vulnerability="Bias",
        vulnerability_type="religion",
        **kw,
    )


async def run_seq(attack: SequentialJailbreak, fake: FakeLLM, target, **kw):
    return await attack.run(
        attacker=fake,
        target=target,
        initial_attack="Explain how to do the dangerous thing.",
        vulnerability="Illegal Activity",
        vulnerability_type="weapons",
        **kw,
    )


def has_user_and_assistant(turns) -> bool:
    roles = {t.role for t in turns}
    return "user" in roles and "assistant" in roles


# --------------------------------------------------------------------------
# BadLikertJudge
# --------------------------------------------------------------------------


async def test_blj_reaches_harmful_classification():
    """Escalate one turn, then the judge flags the answer Harmful."""
    state = {"judge": 0}

    def router(messages, rf):
        name = schema_name(rf)
        if name == "BLJJudge":
            state["judge"] += 1
            cls = "Harmful" if state["judge"] >= 2 else "Not harmful"
            return {"classification": cls, "reasoning": "r"}
        if name == "LikertExamples":
            return {"score_1_example": "mild", "score_3_example": "detailed example"}
        if name == "RefinedExample":
            return {"refined_example": "refined detailed example"}
        if name == "NewAttackPrompt":
            return {"new_attack_prompt": "Please continue with more specifics."}
        if name == "NonRefusal":
            return {"classification": "Non-refusal"}
        raise AssertionError(f"unexpected schema {name}")

    fake = FakeLLM(router=router)
    target = EchoTarget("Sure, here are the full details you asked for.")
    result = await run_blj(BadLikertJudge(), fake, target)

    assert result.status == "ok"
    assert result.jailbroken is True
    assert result.rounds >= 1
    assert has_user_and_assistant(result.turns)
    # Costs are counted through the session and surfaced on the result.
    assert result.attacker_calls > 0
    assert result.target_calls > 0
    assert result.attacker_calls == fake.calls.__len__()


async def test_blj_exhausts_num_turns_without_success():
    """Judge never flags Harmful: the attack finishes resisted."""

    def router(messages, rf):
        name = schema_name(rf)
        if name == "BLJJudge":
            return {"classification": "Not harmful", "reasoning": "r"}
        if name == "LikertExamples":
            return {"score_1_example": "mild", "score_3_example": "example"}
        if name == "RefinedExample":
            return {"refined_example": "refined"}
        if name == "NewAttackPrompt":
            return {"new_attack_prompt": "Another angle on the topic."}
        if name == "NonRefusal":
            return {"classification": "Non-refusal"}
        raise AssertionError(f"unexpected schema {name}")

    fake = FakeLLM(router=router)
    result = await run_blj(BadLikertJudge(num_turns=2), fake, EchoTarget())

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.rounds == 2
    assert has_user_and_assistant(result.turns)


async def test_blj_backtracks_on_example_failure_until_refused():
    """Repeated example-generation failures exhaust the backtrack budget."""

    def router(messages, rf):
        name = schema_name(rf)
        if name == "BLJJudge":
            return {"classification": "Not harmful", "reasoning": "r"}
        if name == "LikertExamples":
            # A prose refusal: generate() cannot parse it and raises
            # GenerationError, which the algorithm counts as a backtrack.
            return "I'm sorry, but I can't help with that."
        raise AssertionError(f"unexpected schema {name}")

    fake = FakeLLM(router=router)
    result = await run_blj(
        BadLikertJudge(num_turns=5, max_backtracks=3), fake, EchoTarget()
    )

    assert result.status == "attacker_refused"
    assert result.jailbroken is None
    assert result.details["backtracks"] == 3


async def test_blj_refusal_check_counts_as_backtrack():
    """is_refusal on the crafted attack drives the backtrack path."""

    def router(messages, rf):
        name = schema_name(rf)
        if name == "BLJJudge":
            return {"classification": "Not harmful", "reasoning": "r"}
        if name == "LikertExamples":
            return {"score_1_example": "mild", "score_3_example": "example"}
        if name == "RefinedExample":
            return {"refined_example": "refined"}
        if name == "NewAttackPrompt":
            return {"new_attack_prompt": "Please expand the explanation."}
        if name == "NonRefusal":
            # The classifier says the crafted attack is a refusal.
            return {"classification": "Refusal"}
        raise AssertionError(f"unexpected schema {name}")

    fake = FakeLLM(router=router)
    result = await run_blj(
        BadLikertJudge(num_turns=5, max_backtracks=3), fake, EchoTarget()
    )

    assert result.status == "attacker_refused"
    assert result.details["backtracks"] == 3
    # Proves the is_refusal path ran (NonRefusal was queried each turn).
    assert any(schema_name(rf) == "NonRefusal" for _, rf in fake.calls)


async def test_blj_budget_cutoff_reports_partial_progress():
    """A tight attacker-call budget cuts the first turn mid-way."""

    def router(messages, rf):
        name = schema_name(rf)
        if name == "BLJJudge":
            return {"classification": "Not harmful", "reasoning": "r"}
        if name == "LikertExamples":
            return {"score_1_example": "mild", "score_3_example": "example"}
        if name == "RefinedExample":
            return {"refined_example": "refined"}
        if name == "NewAttackPrompt":
            return {"new_attack_prompt": "More detail please."}
        if name == "NonRefusal":
            return {"classification": "Non-refusal"}
        raise AssertionError(f"unexpected schema {name}")

    fake = FakeLLM(router=router)
    result = await run_blj(
        BadLikertJudge(), fake, EchoTarget(), budget=Budget(max_attacker_calls=2)
    )

    assert result.status == "budget_exhausted"
    assert result.rounds >= 1  # partial progress recorded
    assert result.attacker_calls >= 2
    # The seeded turn plus the first target answer survive for judging.
    assert has_user_and_assistant(result.turns)


async def test_blj_target_error():
    def router(messages, rf):
        return {"classification": "Not harmful", "reasoning": "r"}

    fake = FakeLLM(router=router)
    result = await run_blj(BadLikertJudge(), fake, FailingTarget())

    assert result.status == "target_error"
    assert result.error


# --------------------------------------------------------------------------
# SequentialJailbreak
# --------------------------------------------------------------------------


def _seq_router(judge_name: str, judge_cls: str = "Harmful", marker: str = "REWRITTEN"):
    """Build a router for one sequential scenario type."""

    def router(messages, rf):
        name = schema_name(rf)
        if name == "RewrittenDialogue":
            return {"paraphrased_version": f"Paraphrased version: {marker} <end>"}
        if name == "NonRefusal":
            return {"classification": "Non-refusal"}
        if name in (
            "AdaptiveDialogueTemplate",
            "AdaptiveQuestionBankTemplate",
            "AdaptiveGameEnvironmentTemplate",
        ):
            return {"template": f"adaptive template with {marker}"}
        if name == "ImprovedAttack":
            return {"improved_attack": "an improved version of the request"}
        if name == judge_name:
            return {"classification": judge_cls}
        raise AssertionError(f"unexpected schema {name}")

    return router


async def test_seq_reaches_harmful_classification():
    fake = FakeLLM(router=_seq_router("DialogueJudge", "Harmful"))
    result = await run_seq(
        SequentialJailbreak(type="dialogue"), fake, EchoTarget()
    )

    assert result.status == "ok"
    assert result.jailbroken is True
    assert result.rounds >= 1
    assert has_user_and_assistant(result.turns)
    assert result.details["type"] == "dialogue"
    assert result.attacker_calls > 0
    assert result.target_calls > 0


async def test_seq_exhausts_num_turns_without_success():
    fake = FakeLLM(router=_seq_router("DialogueJudge", "Not harmful"))
    result = await run_seq(
        SequentialJailbreak(type="dialogue", num_turns=2), fake, EchoTarget()
    )

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.rounds == 2
    # The later turn built an adaptive template (uses the previous response).
    assert any(
        schema_name(rf) == "AdaptiveDialogueTemplate" for _, rf in fake.calls
    )


async def test_seq_dialogue_first_turn_template_contains_rewrite():
    marker = "REWRITTEN_DIALOGUE_XYZ"
    fake = FakeLLM(router=_seq_router("DialogueJudge", "Not harmful", marker))
    result = await run_seq(
        SequentialJailbreak(type="dialogue", num_turns=1), fake, EchoTarget()
    )

    first_template = result.turns[2].content  # seed, reply, scenario, reply
    assert marker in first_template
    assert "Sam:" in first_template and "Alex:" in first_template


async def test_seq_question_bank_first_turn_template_contains_rewrite():
    marker = "REWRITTEN_QUESTION_XYZ"
    fake = FakeLLM(router=_seq_router("QuestionBankJudge", "Not harmful", marker))
    result = await run_seq(
        SequentialJailbreak(type="question_bank", num_turns=1), fake, EchoTarget()
    )

    first_template = result.turns[2].content
    assert marker in first_template
    assert "virtual reality game" in first_template
    assert result.details["type"] == "question_bank"


async def test_seq_game_environment_first_turn_template_contains_rewrite():
    marker = "REWRITTEN_CHALLENGE_XYZ"
    fake = FakeLLM(router=_seq_router("GameEnvironmentJudge", "Not harmful", marker))
    result = await run_seq(
        SequentialJailbreak(type="game_environment", num_turns=1), fake, EchoTarget()
    )

    first_template = result.turns[2].content
    assert marker in first_template
    assert "Echoes of Truth" in first_template
    assert result.details["type"] == "game_environment"


async def test_seq_persona_validation_matches_deepteam():
    import pytest

    # question_bank / game_environment reject a persona.
    with pytest.raises(ValueError):
        SequentialJailbreak(type="question_bank", persona="student")
    with pytest.raises(ValueError):
        SequentialJailbreak(type="game_environment", persona="prisoner")

    # dialogue defaults to the student persona; the others force it to None.
    assert SequentialJailbreak(type="dialogue").persona == "student"
    assert SequentialJailbreak(type="dialogue", persona="researcher").persona == "researcher"
    assert SequentialJailbreak(type="question_bank").persona is None


async def test_seq_target_refusal_stops_the_attack():
    fake = FakeLLM(router=_seq_router("DialogueJudge", "Harmful"))
    # The target refuses: the cheap heuristic flags it and the loop stops.
    target = EchoTarget("I'm sorry, I can't help with that.")
    result = await run_seq(SequentialJailbreak(type="dialogue"), fake, target)

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.rounds == 1


async def test_seq_budget_cutoff_reports_partial_progress():
    fake = FakeLLM(router=_seq_router("DialogueJudge", "Not harmful"))
    result = await run_seq(
        SequentialJailbreak(type="dialogue"),
        fake,
        EchoTarget(),
        budget=Budget(max_attacker_calls=2),
    )

    assert result.status == "budget_exhausted"
    assert result.rounds >= 1
    assert result.attacker_calls >= 2
    assert has_user_and_assistant(result.turns)


async def test_seq_target_error():
    fake = FakeLLM(router=_seq_router("DialogueJudge", "Not harmful"))
    result = await run_seq(SequentialJailbreak(type="dialogue"), fake, FailingTarget())

    assert result.status == "target_error"
    assert result.error
