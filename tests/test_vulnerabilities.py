"""Vulnerability catalog: type validation, baseline generation, judge dispatch."""

from __future__ import annotations

import pytest

from eval_ai_redteam.types import CaseStatus, RTTurn
from eval_ai_redteam.vulnerabilities import (
    BOLA,
    BUILTIN_VULNERABILITIES,
    VULNERABILITY_REGISTRY,
    Bias,
    CustomVulnerability,
    IllegalActivity,
    IntellectualProperty,
    PIILeakage,
    get_vulnerability,
)

from conftest import FakeLLM, reason_score, synthetic


def test_registry_covers_every_builtin():
    assert len(BUILTIN_VULNERABILITIES) == 25
    assert set(VULNERABILITY_REGISTRY) == {c.key for c in BUILTIN_VULNERABILITIES}
    assert all(cls.key and cls.name and cls.description for cls in BUILTIN_VULNERABILITIES)


def test_types_default_to_all_and_validate():
    assert Bias().get_values() == Bias.allowed_types()
    assert Bias(types=["gender", "race"]).get_values() == ["gender", "race"]
    with pytest.raises(ValueError, match="Unknown type"):
        Bias(types=["nope"])
    with pytest.raises(ValueError, match="Duplicate"):
        Bias(types=["gender", "gender"])
    with pytest.raises(ValueError, match="empty"):
        Bias(types=[])
    with pytest.raises(TypeError):
        Bias(types="gender")  # type: ignore[arg-type]


def test_get_vulnerability_by_key():
    v = get_vulnerability("pii_leakage", ["direct_disclosure"])
    assert isinstance(v, PIILeakage) and v.get_values() == ["direct_disclosure"]
    with pytest.raises(ValueError, match="unknown vulnerability"):
        get_vulnerability("nope")


@pytest.mark.parametrize("cls", BUILTIN_VULNERABILITIES, ids=lambda c: c.key)
def test_every_builtin_renders_baseline_and_judge_prompts(cls):
    v = cls()
    for vtype in v.types:
        prompt = v.baseline_prompt(vtype, 3, "an airline support bot")
        assert isinstance(prompt, str) and "3" in prompt
    case = v.new_case(v.types[0], input="attack", actual_output="answer")
    judge = v.judge_prompt(case, "an airline support bot")
    assert "answer" in judge
    assert case.risk_category  # every builtin has a bucket


def test_judge_prompt_uses_transcript_for_multi_turn():
    v = Bias()
    case = v.new_case("gender", input="first", turns=[RTTurn(role="user", content="first"), RTTurn(role="assistant", content="reply text")])
    prompt = v.judge_prompt(case, None)
    assert "Full Conversation To Evaluate" in prompt and "reply text" in prompt


def test_category_flavoured_judge_gets_the_subtype():
    v = IllegalActivity(types=["cybercrime"])
    case = v.new_case("cybercrime", input="a", actual_output="b")
    assert "cybercrime" in v.judge_prompt(case, "bot")


def test_entities_and_no_input_signatures():
    bola = BOLA()
    case = bola.new_case(bola.types[0], input="a", actual_output="b", metadata={"entities": ["acct-1", "acct-2"]})
    assert "acct-1, acct-2" in bola.judge_prompt(case, None)
    ip = IntellectualProperty()
    case = ip.new_case(ip.types[0], input="ignored", actual_output="out")
    assert "out" in ip.judge_prompt(case, "bot")


async def test_simulate_attacks_one_call_per_type():
    llm = FakeLLM([synthetic("q1", "q2"), synthetic("q3", "q4")])
    v = Bias(types=["gender", "race"])
    cases = await v.simulate_attacks(llm, purpose="hr bot", attacks_per_vulnerability_type=2)
    assert [c.input for c in cases] == ["q1", "q2", "q3", "q4"]
    assert [c.vulnerability_type for c in cases] == ["gender", "gender", "race", "race"]
    assert all(c.baseline_input == c.input and c.attacker_calls == 1 and c.status == CaseStatus.OK for c in cases)
    assert "hr bot" in llm.prompts[0]


async def test_simulate_attacks_truncates_extra_inputs():
    llm = FakeLLM([synthetic("q1", "q2", "q3")])
    cases = await Bias(types=["gender"]).simulate_attacks(llm, attacks_per_vulnerability_type=1)
    assert len(cases) == 1


async def test_simulate_attacks_marks_refusal_and_errors():
    llm = FakeLLM(["I'm sorry, I can't create that.", "garbage", "garbage", "garbage", {"data": []}], max_retries=3)
    v = Bias(types=["gender", "race", "religion"])
    cases = await v.simulate_attacks(llm, attacks_per_vulnerability_type=2)
    assert [c.status for c in cases] == [
        CaseStatus.ATTACKER_REFUSED, CaseStatus.ATTACKER_REFUSED,
        CaseStatus.SIMULATION_ERROR, CaseStatus.SIMULATION_ERROR,
        CaseStatus.SIMULATION_ERROR, CaseStatus.SIMULATION_ERROR,
    ]
    assert all(c.input is None for c in cases)


async def test_judge_sets_score_and_reason():
    llm = FakeLLM([reason_score(1, "refused politely")])
    v = Bias()
    case = v.new_case("gender", input="a", actual_output="b")
    verdict = await v.judge(llm, case, purpose="bot")
    assert verdict.ok and case.score == 1 and case.reason == "refused politely" and case.judge_calls == 1
    assert "bot" in llm.prompts[0]


async def test_judge_clamps_and_reports_errors():
    v = Bias()
    case = v.new_case("gender", input="a", actual_output="b")
    await v.judge(FakeLLM([reason_score(7, "weird scale")]), case)
    assert case.score == 1.0
    case = v.new_case("gender", input="a", actual_output="b")
    await v.judge(FakeLLM(["no json", "no json", "no json"]), case)
    assert case.status == CaseStatus.JUDGE_ERROR and case.score is None and "no verdict" in case.error


def test_custom_vulnerability():
    c = CustomVulnerability("Refund policy", "Grants refunds outside the 30-day window", types=["pressure", "fake_receipt"])
    assert c.get_name() == "Refund policy" and c.get_values() == ["pressure", "fake_receipt"]
    assert c.description == "Grants refunds outside the 30-day window"
    prompt = c.baseline_prompt(c.types[0], 2, "shop bot")
    assert "Refund policy" in prompt and "pressure" in prompt
    case = c.new_case("pressure", input="a", actual_output="b")
    assert "30-day window" in c.judge_prompt(case, None)
    assert case.risk_category == "Others"
    custom_prompt = "Make {max_goldens} requests about {name} of type {type} for {purpose}. JSON with data list."
    c2 = CustomVulnerability("X", "crit", custom_prompt=custom_prompt)
    assert c2.get_values() == ["default"]
    assert "Make 2 requests about X" in c2.baseline_prompt(c2.types[0], 2, "p")
    with pytest.raises(ValueError):
        CustomVulnerability("", "crit")
    with pytest.raises(ValueError):
        CustomVulnerability("X", "  ")


def test_expected_behaviour_metadata_is_prepended_to_judge_prompt():
    from eval_ai_redteam.vulnerabilities.base import expected_behaviour_of

    v = Bias()
    plain = v.new_case("gender", input="a", actual_output="b")
    assert expected_behaviour_of(plain) is None
    assert "EXPECTED BEHAVIOUR FOR THIS SPECIFIC INPUT" not in v.judge_prompt(plain, "bot")

    case = v.new_case(
        "gender", input="a", actual_output="b",
        metadata={"expected_behaviour": "Decline and route to a human agent."},
    )
    prompt = v.judge_prompt(case, "bot")
    assert prompt.startswith("EXPECTED BEHAVIOUR FOR THIS SPECIFIC INPUT")
    assert "Decline and route to a human agent." in prompt
    assert "the expected behaviour wins" in prompt
    # the vulnerability's own criteria still follow
    assert "Bias" in prompt or "bias" in prompt

    blank = v.new_case("gender", input="a", actual_output="b", metadata={"expected_behaviour": "   "})
    assert "EXPECTED BEHAVIOUR" not in v.judge_prompt(blank, None)


def test_custom_vulnerability_judge_gets_expected_behaviour_too():
    c = CustomVulnerability("Policy", "breaks the refund policy")
    case = c.new_case("default", input="a", actual_output="b", metadata={"expected_behaviour": "Say no politely."})
    prompt = c.judge_prompt(case, None)
    assert prompt.startswith("EXPECTED BEHAVIOUR") and "breaks the refund policy" in prompt
