"""Union of every built-in vulnerability type enum (for typing and risks)."""

from __future__ import annotations

from typing import Union

from .bfla.types import BFLAType
from .bias.types import BiasType
from .bola.types import BOLAType
from .child_protection.types import ChildProtectionType
from .competition.types import CompetitionType
from .debug_access.types import DebugAccessType
from .ethics.types import EthicsType
from .excessive_agency.types import ExcessiveAgencyType
from .fairness.types import FairnessType
from .graphic_content.types import GraphicContentType
from .illegal_activity.types import IllegalActivityType
from .indirect_instruction.types import IndirectInstructionType
from .intellectual_property.types import IntellectualPropertyType
from .misinformation.types import MisinformationType
from .personal_safety.types import PersonalSafetyType
from .pii_leakage.types import PIILeakageType
from .prompt_leakage.types import PromptLeakageType
from .rbac.types import RBACType
from .robustness.types import RobustnessType
from .shell_injection.types import ShellInjectionType
from .sql_injection.types import SQLInjectionType
from .ssrf.types import SSRFType
from .system_reconnaissance.types import SystemReconnaissanceType
from .toxicity.types import ToxicityType
from .unexpected_code_execution.types import UnexpectedCodeExecutionType

VulnerabilityType = Union[
    BFLAType,
    BiasType,
    BOLAType,
    ChildProtectionType,
    CompetitionType,
    DebugAccessType,
    EthicsType,
    ExcessiveAgencyType,
    FairnessType,
    GraphicContentType,
    IllegalActivityType,
    IndirectInstructionType,
    IntellectualPropertyType,
    MisinformationType,
    PersonalSafetyType,
    PIILeakageType,
    PromptLeakageType,
    RBACType,
    RobustnessType,
    ShellInjectionType,
    SQLInjectionType,
    SSRFType,
    SystemReconnaissanceType,
    ToxicityType,
    UnexpectedCodeExecutionType,
]

__all__ = ["VulnerabilityType"] + [n for n in dir() if n.endswith("Type") and n != "VulnerabilityType"]
