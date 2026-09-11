"""OWASP / NIST / MITRE tables build, filter and run end to end with fakes."""

from __future__ import annotations

import pytest

from eval_ai_redteam import RedTeamer
from eval_ai_redteam.attacks.base import BaseAttack
from eval_ai_redteam.frameworks import FRAMEWORKS, MITRE, NIST, OWASPTop10
from eval_ai_redteam.types import CaseStatus
from eval_ai_redteam.vulnerabilities import BaseVulnerability, CustomVulnerability

from conftest import EchoTarget, FakeLLM, reason_score, synthetic

EXPECTED_CATEGORIES = {
    OWASPTop10: 10,
    NIST: 4,
    MITRE: 6,
}


@pytest.mark.parametrize("cls,count", EXPECTED_CATEGORIES.items(), ids=lambda x: getattr(x, "__name__", x))
def test_framework_tables_build(cls, count):
    fw = cls()
    assert len(fw.risk_categories) == count
    assert fw.get_name()
    for category in fw.risk_categories:
        assert category.name and category.display_name
        assert category.vulnerabilities, category.name
        assert all(isinstance(v, BaseVulnerability) for v in category.vulnerabilities)
        assert all(isinstance(a, BaseAttack) for a in category.attacks)
        assert all(a.weight >= 0 for a in category.attacks)
        assert "—" not in (category.display_name or "") and "–" not in (category.display_name or "")
    assert len(fw.vulnerabilities) == sum(len(c.vulnerabilities) for c in fw.risk_categories)


def test_framework_category_filter():
    fw = OWASPTop10(categories=["LLM_02", "LLM_01"])
    assert fw.categories == ["LLM_02", "LLM_01"]
    assert [c.name for c in fw.risk_categories] == ["LLM_02", "LLM_01"]
    with pytest.raises(ValueError, match="unknown categories"):
        OWASPTop10(categories=["LLM_99"])
    assert OWASPTop10.allowed_categories() == [f"LLM_{i:02d}" for i in range(1, 11)]


def test_framework_registry():
    assert set(FRAMEWORKS) == {"owasp", "nist", "mitre"}
    assert FRAMEWORKS["owasp"] is OWASPTop10


def test_mitre_impact_uses_custom_recursive_hijacking():
    impact = [c for c in MITRE().risk_categories if c.name == "impact"][0]
    customs = [v for v in impact.vulnerabilities if isinstance(v, CustomVulnerability)]
    assert any(v.get_name() == "Recursive Hijacking" for v in customs)


def _generic_router(messages, response_format):
    name = (response_format or {}).get("json_schema", {}).get("name")
    if name == "SyntheticDataList":
        return synthetic("seed")
    if name == "ReasonScore":
        return reason_score(1, "safe")
    # every technique / multi-turn schema: unparseable, so the technique
    # fails and the engine falls back to sending the baseline
    return "not json"


async def test_framework_category_runs_end_to_end():
    fw = OWASPTop10(categories=["LLM_07"])
    rt = RedTeamer(attacker=FakeLLM(router=_generic_router, max_retries=1), judge=FakeLLM(router=_generic_router), purpose="bot")
    target = EchoTarget()
    ra = await rt.red_team(target, framework=fw)
    expected = sum(len(v.types) for c in fw.risk_categories for v in c.vulnerabilities)
    assert ra.overview.total == expected
    assert set(ra.categories) == {"LLM_07"}
    allowed = {CaseStatus.OK, CaseStatus.TECHNIQUE_FAILED, CaseStatus.ATTACKER_REFUSED}
    assert all(c.status in allowed for c in ra.test_cases)
    assert all(c.metadata["framework_category"] == "LLM_07" for c in ra.test_cases)
    judged = [c for c in ra.test_cases if c.status == CaseStatus.OK]
    assert judged and all(c.score == 1.0 for c in judged)
