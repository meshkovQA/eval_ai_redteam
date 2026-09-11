"""Async ports of Linear / Crescendo / Tree jailbreaking.

Every test drives a real ``BaseMultiTurnAttack.run`` against an
``EchoTarget`` (or a refusing / failing target) with a ``FakeLLM`` attacker
whose answers are chosen by a ``router`` that inspects the requested schema
name (``response_format["json_schema"]["name"]``) and the prompt text. The
base ``run`` converts every failure mode into a typed ``MultiTurnResult``.
"""

from __future__ import annotations

import json
from typing import Optional

import pytest

from eval_ai_redteam.attacks.multi_turn import (
    CrescendoJailbreaking,
    LinearJailbreaking,
    TreeJailbreaking,
)
from eval_ai_redteam.types import Budget, RTTurn

from conftest import EchoTarget, FailingTarget, FakeLLM


# ----------------------------------------------------------------------
# Router helpers
# ----------------------------------------------------------------------


def schema_name(response_format: Optional[dict]) -> Optional[str]:
    if not response_format:
        return None
    return response_format.get("json_schema", {}).get("name")


def make_attacker(schema_answers: dict[str, object], *, name: str = "attacker") -> FakeLLM:
    """Attacker that answers by requested schema name.

    ``schema_answers`` maps a pydantic schema name to the value to return
    (a dict or pydantic model). When the schema is not in the map the fake
    falls back to the prompt-steered path, which still carries the schema
    name, so an unmapped schema raises a clear error.
    """

    def router(messages, response_format):
        name_ = schema_name(response_format)
        if name_ is None:
            # Prompt-steered fallback: recover the schema from the field hints
            # the llm layer appends. Tests keep native structured output on,
            # so this path is only hit if a schema is missing from the map.
            for key in schema_answers:
                if key in messages[-1]["content"]:
                    name_ = key
                    break
        if name_ not in schema_answers:
            raise AssertionError(f"router has no answer for schema {name_!r}")
        answer = schema_answers[name_]
        return answer(messages) if callable(answer) else answer

    return FakeLLM(router=router, name=name)


# ======================================================================
# LinearJailbreaking
# ======================================================================


@pytest.mark.asyncio
async def test_linear_reaches_jailbreak():
    attacker = make_attacker(
        {
            "Feedback": {"jailbroken": True, "suggestion": "done"},
            "Improvement": {"reasoning": "r", "new_prompt": "p"},
        }
    )
    target = EchoTarget("Sure, step one is...")
    attack = LinearJailbreaking(num_turns=5)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="tell me how"
    )

    assert result.status == "ok"
    assert result.jailbroken is True
    assert result.rounds == 1
    assert any(t.role == "user" for t in result.turns)
    assert any(t.role == "assistant" for t in result.turns)
    assert result.attacker_calls == 1  # the single judge call
    assert result.target_calls == 1  # ensure_assistant_reply only


@pytest.mark.asyncio
async def test_linear_exhausts_without_jailbreak():
    attacker = make_attacker(
        {
            "Feedback": {"jailbroken": False, "suggestion": "try harder"},
            "Improvement": {"reasoning": "r", "new_prompt": "a bolder benign ask"},
            "NonRefusal": {"classification": "Non-refusal"},
        }
    )
    target = EchoTarget("Here is a safe general answer.")
    attack = LinearJailbreaking(num_turns=3)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="seed"
    )

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.rounds == 3
    # 3 turns sent on top of the seed reply.
    assert sum(1 for t in result.turns if t.role == "user") == 4
    assert result.target_calls == 4  # seed + 3 loop turns


@pytest.mark.asyncio
async def test_linear_attacker_refusal_raises():
    attacker = make_attacker(
        {
            "Feedback": {"jailbroken": False, "suggestion": "s"},
            "Improvement": {
                "reasoning": "r",
                "new_prompt": "I'm sorry, I cannot help with that.",
            },
        }
    )
    target = EchoTarget("safe")
    attack = LinearJailbreaking(num_turns=5)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="seed"
    )

    assert result.status == "attacker_refused"
    assert result.jailbroken is None  # _run raised before returning
    assert result.rounds == 1


@pytest.mark.asyncio
async def test_linear_budget_cutoff():
    attacker = make_attacker(
        {
            "Feedback": {"jailbroken": False, "suggestion": "s"},
            "Improvement": {"reasoning": "r", "new_prompt": "a benign escalation"},
            "NonRefusal": {"classification": "Non-refusal"},
        }
    )
    target = EchoTarget("safe")
    attack = LinearJailbreaking(num_turns=5)

    # judge (1) + improvement (2) + is_refusal classifier (3 -> over cap).
    result = await attack.run(
        attacker=attacker,
        target=target,
        initial_attack="seed",
        budget=Budget(max_attacker_calls=2),
    )

    assert result.status == "budget_exhausted"
    assert result.rounds == 1
    assert result.turns  # partial transcript kept (seed + its reply)
    assert any(t.role == "assistant" for t in result.turns)
    assert result.attacker_calls == 3  # the call that tripped the cap is counted


@pytest.mark.asyncio
async def test_linear_target_error():
    attacker = make_attacker({"Feedback": {"jailbroken": False, "suggestion": "s"}})
    attack = LinearJailbreaking(num_turns=5)

    result = await attack.run(
        attacker=attacker, target=FailingTarget(), initial_attack="seed"
    )

    assert result.status == "target_error"
    assert result.target_calls == 1


# ======================================================================
# CrescendoJailbreaking
# ======================================================================


@pytest.mark.asyncio
async def test_crescendo_reaches_jailbreak():
    attacker = make_attacker(
        {
            "AttackData": {
                "generated_question": "what is the history of X?",
                "last_response_summary": "",
                "rationale_behind_jailbreak": "warm up",
            },
            "RefusalData": {"value": False, "rationale": "answered", "metadata": 10},
            "EvalData": {
                "value": True,
                "description": "d",
                "rationale": "fully answered",
                "metadata": 100,
            },
        }
    )
    target = EchoTarget("Sure, here is the detailed answer.")
    attack = CrescendoJailbreaking(max_rounds=5, max_backtracks=3)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="the objective"
    )

    assert result.status == "ok"
    assert result.jailbroken is True
    assert result.rounds == 1
    assert result.details["backtracks"] == 0
    assert result.details["eval_percentage"] == 100
    assert any(t.role == "user" for t in result.turns)
    assert any(t.role == "assistant" for t in result.turns)
    assert result.attacker_calls == 3  # attack + refusal + eval


@pytest.mark.asyncio
async def test_crescendo_exhausts_without_jailbreak():
    attacker = make_attacker(
        {
            "AttackData": {
                "generated_question": "q",
                "last_response_summary": "",
                "rationale_behind_jailbreak": "r",
            },
            "RefusalData": {"value": False, "rationale": "ok", "metadata": 10},
            "EvalData": {
                "value": False,
                "description": "d",
                "rationale": "not yet",
                "metadata": 30,
            },
        }
    )
    target = EchoTarget("A partial, safe answer.")
    attack = CrescendoJailbreaking(max_rounds=2, max_backtracks=5)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="objective"
    )

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.rounds == 2
    assert result.details["backtracks"] == 0


@pytest.mark.asyncio
async def test_crescendo_backtracks_and_stops_after_max_backtracks():
    attacker = make_attacker(
        {
            "AttackData": {
                "generated_question": "q",
                "last_response_summary": "",
                "rationale_behind_jailbreak": "r",
            },
            "RefusalData": {"value": True, "rationale": "refused", "metadata": 99},
            "EvalData": {
                "value": False,
                "description": "d",
                "rationale": "n",
                "metadata": 0,
            },
        }
    )
    target = EchoTarget("I'm sorry, I can't help with that.")
    attack = CrescendoJailbreaking(max_rounds=10, max_backtracks=2)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="objective"
    )

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.details["backtracks"] == 2
    # Seed pair + the last refused pair (the backtracked pair was truncated).
    assert len(result.turns) == 4
    assert [t.role for t in result.turns] == ["user", "assistant", "user", "assistant"]


@pytest.mark.asyncio
async def test_crescendo_budget_cutoff():
    attacker = make_attacker(
        {
            "AttackData": {
                "generated_question": "q",
                "last_response_summary": "",
                "rationale_behind_jailbreak": "r",
            },
            "RefusalData": {"value": False, "rationale": "ok", "metadata": 10},
            "EvalData": {
                "value": False,
                "description": "d",
                "rationale": "n",
                "metadata": 20,
            },
        }
    )
    target = EchoTarget("safe answer")
    attack = CrescendoJailbreaking(max_rounds=5, max_backtracks=5)

    # round 1: attack (1) + refusal (2) + eval (3 -> over cap).
    result = await attack.run(
        attacker=attacker,
        target=target,
        initial_attack="objective",
        budget=Budget(max_attacker_calls=2),
    )

    assert result.status == "budget_exhausted"
    assert result.rounds == 1
    assert result.turns
    assert any(t.role == "assistant" for t in result.turns)
    assert result.attacker_calls == 3


@pytest.mark.asyncio
async def test_crescendo_target_error():
    attacker = make_attacker(
        {
            "AttackData": {
                "generated_question": "q",
                "last_response_summary": "",
                "rationale_behind_jailbreak": "r",
            }
        }
    )
    attack = CrescendoJailbreaking(max_rounds=5)

    result = await attack.run(
        attacker=attacker, target=FailingTarget(), initial_attack="objective"
    )

    assert result.status == "target_error"
    assert result.target_calls == 1


# ======================================================================
# TreeJailbreaking
# ======================================================================


def tree_attacker(rating: int, *, classification: str = "Non-refusal") -> FakeLLM:
    return make_attacker(
        {
            "ImprovementPrompt": {"improvement": "i", "prompt": "a refined benign ask"},
            "NonRefusal": {"classification": classification},
            "Rating": {"rating": rating},
        }
    )


@pytest.mark.asyncio
async def test_tree_reaches_jailbreak():
    attacker = tree_attacker(rating=10)
    target = EchoTarget("Yes, I can help you with that.")
    attack = TreeJailbreaking(max_depth=2, max_seconds=30)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="goal"
    )

    assert result.status == "ok"
    assert result.jailbroken is True
    assert result.details["best_score"] == 10
    assert result.rounds >= 1
    assert any(t.role == "user" for t in result.turns)
    assert any(t.role == "assistant" for t in result.turns)
    # Early-terminate after the first full expansion found a top-rated child.
    assert result.details["nodes_expanded"] == 1


@pytest.mark.asyncio
async def test_tree_exhausts_without_jailbreak():
    attacker = tree_attacker(rating=1)
    target = EchoTarget("A safe, unhelpful answer.")
    attack = TreeJailbreaking(max_depth=2, max_seconds=30)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="goal"
    )

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.details["best_score"] == 1
    assert result.rounds > 0
    assert any(t.role == "assistant" for t in result.turns)


@pytest.mark.asyncio
async def test_tree_pruning_and_depth_bound_target_calls():
    # All children score 0 -> every branch is pruned, so only the root is
    # expanded and no node ever reaches depth 2. Target calls = seed (1) +
    # the branches tried at the root. calculate_branches(0, 0) == 2.
    attacker = tree_attacker(rating=0)
    target = EchoTarget("nope")
    attack = TreeJailbreaking(max_depth=3, max_seconds=30)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="goal"
    )

    assert result.status == "ok"
    assert result.jailbroken is False
    assert result.details["nodes_expanded"] == 1  # only the root expanded
    assert result.target_calls == 3  # seed + 2 pruned branch probes
    # Pruned children never entered the tree, so the transcript is seed-only.
    assert len(result.turns) == 2


@pytest.mark.asyncio
async def test_tree_max_depth_caps_expansion():
    # Non-pruning (rating 1) but max_depth=1: root expands to depth-1 leaves,
    # which cannot expand further. Bounds target calls to seed + root branches.
    attacker = tree_attacker(rating=1)
    target = EchoTarget("safe")
    attack = TreeJailbreaking(max_depth=1, max_seconds=30)

    result = await attack.run(
        attacker=attacker, target=target, initial_attack="goal"
    )

    assert result.status == "ok"
    # calculate_branches(0, 0) == 2 children created at the root, all depth 1.
    assert result.target_calls == 3  # seed + 2 root branches
    # Every node beyond the root is at max_depth, so nothing else expands.
    assert result.details["nodes_expanded"] >= 1


@pytest.mark.asyncio
async def test_tree_budget_cutoff():
    attacker = tree_attacker(rating=5)
    target = EchoTarget("safe")
    attack = TreeJailbreaking(max_depth=3, max_seconds=30)

    result = await attack.run(
        attacker=attacker,
        target=target,
        initial_attack="goal",
        budget=Budget(max_attacker_calls=2),
    )

    assert result.status == "budget_exhausted"
    assert result.rounds >= 1  # the root expansion was under way
    assert result.turns  # partial transcript (seed pair) kept
    assert result.attacker_calls >= 2


@pytest.mark.asyncio
async def test_tree_target_error():
    attacker = tree_attacker(rating=5)
    attack = TreeJailbreaking(max_depth=2, max_seconds=30)

    result = await attack.run(
        attacker=attacker, target=FailingTarget(), initial_attack="goal"
    )

    assert result.status == "target_error"
    assert result.target_calls == 1


@pytest.mark.asyncio
async def test_counters_match_session_usage():
    # A sanity check that attacker_calls / target_calls are surfaced at all.
    attacker = make_attacker(
        {
            "Feedback": {"jailbroken": True, "suggestion": "done"},
        }
    )
    target = EchoTarget("Sure.")
    result = await LinearJailbreaking(num_turns=2).run(
        attacker=attacker, target=target, initial_attack="x"
    )
    assert result.attacker_calls == len(attacker.calls)
    assert result.target_calls == len(target.calls)
