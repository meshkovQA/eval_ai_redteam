"""OWASP Top 10 for LLMs 2025, NIST AI RMF (Measure), MITRE ATLAS.

The category tables are ported from deepteam (``*_categories`` modules)
and instantiate every vulnerability and attack class they reference, so
they are imported lazily on first use rather than at package import.
"""

from __future__ import annotations

from .base import AISafetyFramework, RiskCategory


class OWASPTop10(AISafetyFramework):
    name = "OWASP Top 10 for LLMs 2025"
    description = (
        "The most critical security risks for LLM applications: prompt injection, "
        "sensitive information disclosure, supply chain, data and model poisoning, "
        "improper output handling, excessive agency, system prompt leakage, "
        "vector and embedding weaknesses, misinformation, unbounded consumption."
    )

    @classmethod
    def get_categories_table(cls) -> list[RiskCategory]:
        from .owasp_categories import OWASP_CATEGORIES

        return OWASP_CATEGORIES


class NIST(AISafetyFramework):
    name = "NIST AI Risk Management Framework (AI RMF)"
    description = (
        "NIST AI RMF Measure function (M.1-M.4): risk metrics, trustworthiness and "
        "safety evaluation, risk tracking, impact and transparency assessment."
    )

    @classmethod
    def get_categories_table(cls) -> list[RiskCategory]:
        from .nist_categories import NIST_CATEGORIES

        return NIST_CATEGORIES


class MITRE(AISafetyFramework):
    name = "MITRE ATLAS"
    description = (
        "Adversarial tactics against AI systems: reconnaissance, resource development, "
        "initial access, ML attack staging, exfiltration, impact."
    )

    @classmethod
    def get_categories_table(cls) -> list[RiskCategory]:
        from .mitre_categories import MITRE_CATEGORIES

        return MITRE_CATEGORIES


FRAMEWORKS: dict[str, type[AISafetyFramework]] = {
    "owasp": OWASPTop10,
    "nist": NIST,
    "mitre": MITRE,
}

__all__ = ["AISafetyFramework", "RiskCategory", "OWASPTop10", "NIST", "MITRE", "FRAMEWORKS"]
