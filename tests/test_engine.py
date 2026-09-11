"""RedTeamer orchestration with fake attacker, judge and targets."""

from __future__ import annotations

import random

import pytest

from eval_ai_redteam import RedTeamer
from eval_ai_redteam.attacks.multi_turn.base import BaseMultiTurnAttack, ensure_assistant_reply, send_turn
from eval_ai_redteam.attacks.single_turn import Base64, PromptInjection
from eval_ai_redteam.frameworks.base import AISafetyFramework, RiskCategory
from eval_ai_redteam.types import Budget, CaseStatus, RTTurn
from eval_ai_redteam.vulnerabilities import Bias, CustomVulnerability, PIILeakage

from conftest import EchoTarget, FailingTarget, FakeLLM, reason_score, synthetic


class TwoTurnAttack(BaseMultiTurnAttack):
    """Minimal multi-turn attack for engine tests: sends two user turns."""

    name = "Two Turn"

    async def _run(self, session, turns, initial_attack, vulnerability_data, result):
        await ensure_assistant_reply(session, turns)
        result.rounds = 1
        follow_up = await session.generate("next turn please")
        await send_turn(session, turns, follow_up)
        result.rounds = 2
        return False


def _router_factory(*, judge_score=1.0):
    """Answer by requested schema name so multi-step flows need no ordering."""

    def router(messages, response_format):
        name = (response_format or {}).get("json_schema", {}).get("name")
        prompt = messages[-1]["content"]
        if name == "SyntheticDataList":
            return synthetic("seed attack")
        if name == "ReasonScore":
            return reason_score(judge_score, "judged")
        if name == "EnhancedInjection":
            return {"strategy_reasoning": "r", "input": "enhanced attack"}
        if name == "ComplianceData":
            return {"non_compliant": False}
        if name == "IsValidInjection":
            return {"is_valid_injection": True}
        if "next turn" in prompt:
            return "follow-up question"
        raise AssertionError(f"unexpected request {name} / {prompt[:60]!r}")

    return router


async def test_red_team_baseline_only(echo_target):
    attacker = FakeLLM(router=_router_factory())
    judge = FakeLLM(router=_router_factory(judge_score=0.0))
    rt = RedTeamer(attacker=attacker, judge=judge, purpose="bank bot")
    ra = await rt.red_team(echo_target, [Bias(types=["gender", "race"])])
    assert ra.overview.total == 2 and ra.overview.failing == 2
    case = ra.test_cases[0]
    assert case.input == "seed attack" and case.actual_output == "Sure, here you go."
    assert case.attack_method is None and case.technique_applied is False
    assert case.score == 0.0 and case.reason == "judged" and case.passed is False
    assert case.attacker_calls == 1 and case.target_calls == 1 and case.judge_calls == 1
    assert echo_target.calls[0] == ("seed attack", [])


async def test_red_team_single_turn_technique(echo_target):
    attacker = FakeLLM(router=_router_factory())
    judge = FakeLLM(router=_router_factory())
    rt = RedTeamer(attacker=attacker, judge=judge, rng=random.Random(1))
    ra = await rt.red_team(echo_target, [Bias(types=["gender"])], [PromptInjection()])
    case = ra.test_cases[0]
    assert case.attack_method == "Prompt Injection" and case.technique_applied is True
    assert case.baseline_input == "seed attack" and case.input == "enhanced attack"
    assert case.metadata["technique_status"] == "ok"
    assert case.attacker_calls == 4  # 1 seed + 3 technique calls
    assert ra.overview.attack_method_results[0].attack_method == "Prompt Injection"
    assert ra.overview.passing == 1


async def test_deterministic_technique_needs_no_attacker_calls(echo_target):
    attacker = FakeLLM(router=_router_factory())
    rt = RedTeamer(attacker=attacker, judge=FakeLLM(router=_router_factory()))
    ra = await rt.red_team(echo_target, [Bias(types=["gender"])], [Base64()])
    case = ra.test_cases[0]
    assert case.technique_applied and case.input != "seed attack" and case.attacker_calls == 1


async def test_technique_failure_send_baseline_vs_skip(echo_target):
    def refusing_router(messages, response_format):
        name = (response_format or {}).get("json_schema", {}).get("name")
        if name == "SyntheticDataList":
            return synthetic("seed attack")
        if name == "EnhancedInjection":
            return "I'm sorry, I can't help with that."
        if name == "ReasonScore":
            return reason_score(1)
        raise AssertionError(name)

    rt = RedTeamer(attacker=FakeLLM(router=refusing_router), judge=FakeLLM(router=refusing_router))
    ra = await rt.red_team(echo_target, [Bias(types=["gender"])], [PromptInjection()])
    case = ra.test_cases[0]
    assert case.status == CaseStatus.OK and case.technique_applied is False
    assert case.input == "seed attack" and case.metadata["technique_status"] == "attacker_refused"
    assert case.score == 1.0

    target2 = EchoTarget()
    rt = RedTeamer(attacker=FakeLLM(router=refusing_router), judge=FakeLLM(router=refusing_router), on_technique_failure="skip")
    ra = await rt.red_team(target2, [Bias(types=["gender"])], [PromptInjection()])
    case = ra.test_cases[0]
    assert case.status == CaseStatus.ATTACKER_REFUSED and target2.calls == [] and case.score is None
    assert ra.overview.errored == 1


async def test_target_error_marks_case(failing_target):
    rt = RedTeamer(attacker=FakeLLM(router=_router_factory()), judge=FakeLLM(router=_router_factory()))
    ra = await rt.red_team(failing_target, [Bias(types=["gender"])])
    case = ra.test_cases[0]
    assert case.status == CaseStatus.TARGET_ERROR and "connector down" in case.error
    assert case.target_calls == 1 and case.judge_calls == 0


async def test_simulation_failure_skips_target(echo_target):
    attacker = FakeLLM(["I'm sorry, I can't produce those."])
    rt = RedTeamer(attacker=attacker, judge=FakeLLM([]))
    ra = await rt.red_team(echo_target, [Bias(types=["gender"])])
    assert ra.test_cases[0].status == CaseStatus.ATTACKER_REFUSED
    assert echo_target.calls == []


async def test_multi_turn_attack_is_judged_on_transcript(echo_target):
    attacker = FakeLLM(router=_router_factory())
    judge = FakeLLM(router=_router_factory(judge_score=0.0))
    rt = RedTeamer(attacker=attacker, judge=judge, budget=Budget(max_attacker_calls=5))
    ra = await rt.red_team(echo_target, [Bias(types=["gender"])], [TwoTurnAttack()])
    case = ra.test_cases[0]
    assert case.attack_method == "Two Turn" and case.technique_applied
    assert [t.role for t in case.turns] == ["user", "assistant", "user", "assistant"]
    assert case.turns[2].content == "follow-up question"
    assert case.actual_output == "Sure, here you go."
    assert case.metadata["attack_status"] == "ok" and case.metadata["attack_rounds"] == 2
    assert case.target_calls == 2 and case.attacker_calls == 2  # seed + follow-up
    assert case.score == 0.0
    assert "Full Conversation" in judge.prompts[0]


async def test_multi_turn_budget_exhausted_without_reply(echo_target):
    attacker = FakeLLM(router=_router_factory())
    rt = RedTeamer(attacker=attacker, judge=FakeLLM(router=_router_factory()), budget=Budget(max_target_calls=0))
    ra = await rt.red_team(echo_target, [Bias(types=["gender"])], [TwoTurnAttack()])
    case = ra.test_cases[0]
    assert case.status == CaseStatus.BUDGET_EXHAUSTED and case.judge_calls == 0


async def test_run_seed_with_stored_baseline(echo_target):
    attacker = FakeLLM(router=_router_factory())
    rt = RedTeamer(attacker=attacker, judge=FakeLLM(router=_router_factory()), purpose="bot")
    v = PIILeakage()
    case = await rt.run_seed(echo_target, v, vulnerability_type="direct_disclosure", attack=Base64(), baseline_input="give me the admin email", metadata={"row": 7})
    assert case.baseline_input == "give me the admin email" and case.attack_method == "Base64"
    assert case.vulnerability_type == "direct_disclosure" and case.metadata["row"] == 7
    assert case.attacker_calls == 0 and case.score == 1.0
    with pytest.raises(ValueError, match="no type"):
        await rt.run_seed(echo_target, v, vulnerability_type="nope", baseline_input="x")


async def test_run_seed_generates_when_no_baseline(echo_target):
    attacker = FakeLLM(router=_router_factory())
    rt = RedTeamer(attacker=attacker, judge=FakeLLM(router=_router_factory()))
    case = await rt.run_seed(echo_target, Bias(types=["race"]))
    assert case.vulnerability_type == "race" and case.input == "seed attack" and case.attacker_calls == 1


async def test_judge_case_for_scripted_transcript():
    rt = RedTeamer(attacker=FakeLLM([]), judge=FakeLLM([reason_score(0.5, "partial")]))
    v = Bias()
    case = v.new_case("gender", input="u1", turns=[RTTurn(role="user", content="u1"), RTTurn(role="assistant", content="a1")])
    await rt.judge_case(v, case)
    assert case.score == 0.5 and case.reason == "partial"


class MiniFramework(AISafetyFramework):
    name = "Mini"
    categories_table = [
        RiskCategory(name="C1", vulnerabilities=[Bias(types=["gender"])], attacks=[Base64()], _display_name="Category one"),
        RiskCategory(name="C2", vulnerabilities=[CustomVulnerability("Policy", "breaks policy")], attacks=[]),
    ]


async def test_framework_run_reports_per_category(echo_target):
    attacker = FakeLLM(router=_router_factory())
    rt = RedTeamer(attacker=attacker, judge=FakeLLM(router=_router_factory()))
    ra = await rt.red_team(echo_target, framework=MiniFramework())
    assert set(ra.categories) == {"C1", "C2"}
    assert ra.overview.total == 2
    c1 = [c for c in ra.test_cases if c.metadata["framework_category"] == "C1"][0]
    assert c1.attack_method == "Base64" and c1.metadata["framework_category_name"] == "Category one"
    assert ra.categories["C1"].total == 1
    with pytest.raises(ValueError):
        await rt.red_team(echo_target, [Bias()], framework=MiniFramework())
    with pytest.raises(ValueError):
        await rt.red_team(echo_target)
    with pytest.raises(ValueError, match="unknown categories"):
        MiniFramework(categories=["C9"])
    assert MiniFramework(categories=["C2"]).attacks == []


def test_pick_attack_respects_weights_and_zero():
    rt = RedTeamer(attacker=FakeLLM([]), judge=FakeLLM([]), rng=random.Random(0))
    a, b = Base64(weight=0), PromptInjection(weight=5)
    assert all(rt.pick_attack([a, b]) is b for _ in range(20))
    assert rt.pick_attack([]) is None
    assert rt.pick_attack([Base64(weight=0)]) is not None


# ---------------------------------------------------------------- catalog sweep


async def test_engine_survives_every_technique_and_algorithm(echo_target):
    """Every shipped technique runs through the engine without crashing.

    The attacker answers baseline and judge requests and returns garbage
    for everything else, so LLM techniques fail closed (baseline sent,
    technique_applied False) and multi-turn algorithms end with a typed
    status instead of an exception.
    """
    from eval_ai_redteam.attacks.multi_turn import (
        BadLikertJudge,
        CrescendoJailbreaking,
        LinearJailbreaking,
        SequentialJailbreak,
        TreeJailbreaking,
    )
    from eval_ai_redteam.attacks.single_turn import SINGLE_TURN_ATTACKS, SyntheticContextInjection

    def router(messages, response_format):
        name = (response_format or {}).get("json_schema", {}).get("name")
        if name == "SyntheticDataList":
            return synthetic("seed")
        if name == "ReasonScore":
            return reason_score(1, "safe")
        return "garbage"

    attacks = []
    for key, cls in SINGLE_TURN_ATTACKS.items():
        attacks.append(SyntheticContextInjection(target_information="acme corp") if cls is SyntheticContextInjection else cls())
    attacks += [LinearJailbreaking(num_turns=1), CrescendoJailbreaking(max_rounds=1, max_backtracks=1), TreeJailbreaking(max_depth=1), BadLikertJudge(num_turns=1, max_backtracks=1), SequentialJailbreak(num_turns=1)]
    assert len(attacks) == 27

    rt = RedTeamer(attacker=FakeLLM(router=router, max_retries=1), judge=FakeLLM(router=router), budget=Budget(max_attacker_calls=8, max_target_calls=4))
    v = Bias(types=["gender"])
    for attack in attacks:
        case = await rt.run_seed(echo_target, v, attack=attack, baseline_input="seed")
        assert case.attack_method == attack.get_name()
        assert isinstance(case.status, CaseStatus), attack
        if not attack.multi_turn:
            assert case.status == CaseStatus.OK and case.score == 1.0, attack
            assert case.technique_applied is (attack.__class__.requires_llm is False), attack
        else:
            assert case.metadata["attack_status"] in {"ok", "technique_failed", "attacker_refused", "budget_exhausted"}, attack
