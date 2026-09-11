"""Data shapes, budget accounting and overview aggregation."""

from __future__ import annotations

import pytest

from eval_ai_redteam.types import (
    Budget,
    BudgetExhausted,
    CaseStatus,
    RTTestCase,
    RTTurn,
    build_overview,
    build_risk_assessment,
)


def _case(vuln="Bias", vtype="gender", method="Base64", score=None, status=CaseStatus.OK):
    return RTTestCase(
        vulnerability=vuln, vulnerability_type=vtype, attack_method=method, score=score, status=status
    )


def test_passed_semantics():
    assert _case(score=1.0).passed is True
    assert _case(score=0.0).passed is False
    assert _case(score=None).passed is None
    assert _case(score=1.0, status=CaseStatus.JUDGE_ERROR).passed is None


def test_last_assistant_content_prefers_turns():
    case = _case()
    case.actual_output = "single"
    assert case.last_assistant_content == "single"
    case.turns = [RTTurn(role="user", content="u"), RTTurn(role="assistant", content="a1"), RTTurn(role="user", content="u2")]
    assert case.last_assistant_content == "a1"


def test_overview_groups_by_type_and_method():
    cases = [
        _case(score=1.0),
        _case(score=0.0),
        _case(vtype="race", method="ROT-13", score=1.0),
        _case(vtype="race", method="ROT-13", status=CaseStatus.TARGET_ERROR),
        _case(vuln="PII Leakage", vtype="direct_disclosure", method=None, score=0.0),
    ]
    ov = build_overview(cases, run_duration=1.5)
    assert ov.total == 5 and ov.passing == 2 and ov.failing == 2 and ov.errored == 1
    assert ov.pass_rate == pytest.approx(0.5)
    by_type = {(r.vulnerability, r.vulnerability_type): r for r in ov.vulnerability_type_results}
    assert by_type[("Bias", "gender")].pass_rate == pytest.approx(0.5)
    race = by_type[("Bias", "race")]
    assert race.passing == 1 and race.errored == 1 and race.pass_rate == pytest.approx(1.0)
    by_method = {r.attack_method: r for r in ov.attack_method_results}
    assert set(by_method) == {"Base64", "ROT-13"}
    assert ov.run_duration == 1.5


def test_overview_empty():
    ov = build_overview([])
    assert ov.total == 0 and ov.pass_rate == 0.0 and ov.vulnerability_type_results == []


def test_risk_assessment_serialises():
    ra = build_risk_assessment([_case(score=1.0)])
    payload = ra.model_dump()
    assert payload["overview"]["passing"] == 1
    assert payload["test_cases"][0]["status"] == "ok"
    assert ra.categories is None


def test_budget_tracker_limits():
    tracker = Budget(max_attacker_calls=2, max_target_calls=1).start()
    tracker.charge_attacker()
    tracker.charge_attacker()
    with pytest.raises(BudgetExhausted):
        tracker.charge_attacker()
    tracker.charge_target()
    with pytest.raises(BudgetExhausted):
        tracker.charge_target()


def test_budget_time_limit():
    tracker = Budget(max_seconds=0.0).start()
    tracker.started_at -= 1.0
    with pytest.raises(BudgetExhausted):
        tracker.charge_attacker()
