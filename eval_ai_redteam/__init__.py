"""eval_ai_redteam: async red-teaming kernel for LLM applications.

Public surface:

    from eval_ai_redteam import RedTeamer, BaseLLM, CallableLLM
    from eval_ai_redteam.vulnerabilities import Bias, PIILeakage, ...
    from eval_ai_redteam.attacks.single_turn import PromptInjection, Base64, ...
    from eval_ai_redteam.attacks.multi_turn import CrescendoJailbreaking, ...
    from eval_ai_redteam.frameworks import OWASPTop10, NIST, MITRE

The kernel never talks to a provider itself. Callers pass an ``attacker``
and a ``judge`` (both ``BaseLLM``) and a ``target`` coroutine, and get
back ``RTTestCase`` rows with explicit statuses. Nothing is printed,
nothing is uploaded, no thread is spawned.
"""

from .llm import BaseLLM, CallableLLM, GenerationError, looks_like_refusal
from .types import (
    Budget,
    CaseStatus,
    RiskAssessment,
    RTTestCase,
    RTTurn,
    build_overview,
)
from .engine import RedTeamer

__version__ = "0.1.0"

__all__ = [
    "BaseLLM",
    "CallableLLM",
    "GenerationError",
    "looks_like_refusal",
    "Budget",
    "CaseStatus",
    "RiskAssessment",
    "RTTestCase",
    "RTTurn",
    "build_overview",
    "RedTeamer",
    "__version__",
]
