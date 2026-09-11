"""Coarse risk buckets per vulnerability (deepteam's LLMRiskCategories).

Written fresh; the bucket assignments match deepteam 1.0.6 so reports
built on either runtime line up.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class LLMRiskCategories(str, Enum):
    RESPONSIBLE_AI = "Responsible AI"
    ILLEGAL = "Illegal"
    BRAND_IMAGE = "Brand Image"
    DATA_PRIVACY = "Data Privacy"
    UNAUTHORIZED_ACCESS = "Unauthorized Access"
    OTHERS = "Others"


_BY_KEY: dict[str, LLMRiskCategories] = {
    "bias": LLMRiskCategories.RESPONSIBLE_AI,
    "toxicity": LLMRiskCategories.RESPONSIBLE_AI,
    "ethics": LLMRiskCategories.RESPONSIBLE_AI,
    "fairness": LLMRiskCategories.RESPONSIBLE_AI,
    "child_protection": LLMRiskCategories.RESPONSIBLE_AI,
    "illegal_activity": LLMRiskCategories.ILLEGAL,
    "graphic_content": LLMRiskCategories.ILLEGAL,
    "personal_safety": LLMRiskCategories.ILLEGAL,
    "misinformation": LLMRiskCategories.BRAND_IMAGE,
    "excessive_agency": LLMRiskCategories.BRAND_IMAGE,
    "robustness": LLMRiskCategories.BRAND_IMAGE,
    "intellectual_property": LLMRiskCategories.BRAND_IMAGE,
    "competition": LLMRiskCategories.BRAND_IMAGE,
    "prompt_leakage": LLMRiskCategories.DATA_PRIVACY,
    "pii_leakage": LLMRiskCategories.DATA_PRIVACY,
    "system_reconnaissance": LLMRiskCategories.DATA_PRIVACY,
    "bfla": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "bola": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "rbac": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "debug_access": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "shell_injection": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "sql_injection": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "ssrf": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "unexpected_code_execution": LLMRiskCategories.UNAUTHORIZED_ACCESS,
    "indirect_instruction": LLMRiskCategories.UNAUTHORIZED_ACCESS,
}


def get_risk_category(vulnerability: Any, vulnerability_type: str | None = None) -> str:
    """Return the risk bucket for a vulnerability instance or key."""
    key = getattr(vulnerability, "key", None) or str(vulnerability)
    return _BY_KEY.get(key, LLMRiskCategories.OTHERS).value
