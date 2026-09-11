"""Vulnerability catalog: 25 built-in categories plus ``CustomVulnerability``.

Generated once from the deepteam 1.0.6 catalog survey and then maintained
by hand. Each class only binds a name, its type enum and its two ported
prompt templates; all behaviour lives in ``BaseVulnerability``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, Optional, Sequence

from .base import BaseVulnerability

from .bias.types import BiasType
from .bias.template import BiasTemplate as _BiasTemplate
from .bias.judge_template import JudgeTemplate as _BiasJudge
from .toxicity.types import ToxicityType
from .toxicity.template import ToxicityTemplate as _ToxicityTemplate
from .toxicity.judge_template import JudgeTemplate as _ToxicityJudge
from .misinformation.types import MisinformationType
from .misinformation.template import MisinformationTemplate as _MisinformationTemplate
from .misinformation.judge_template import JudgeTemplate as _MisinformationJudge
from .illegal_activity.types import IllegalActivityType
from .illegal_activity.template import IllegalActivityTemplate as _IllegalActivityTemplate
from .illegal_activity.judge_template import JudgeTemplate as _IllegalActivityJudge
from .prompt_leakage.types import PromptLeakageType
from .prompt_leakage.template import PromptLeakageTemplate as _PromptLeakageTemplate
from .prompt_leakage.judge_template import JudgeTemplate as _PromptLeakageJudge
from .pii_leakage.types import PIILeakageType
from .pii_leakage.template import PIILeakageTemplate as _PIILeakageTemplate
from .pii_leakage.judge_template import JudgeTemplate as _PIILeakageJudge
from .bfla.types import BFLAType
from .bfla.template import BFLATemplate as _BFLATemplate
from .bfla.judge_template import JudgeTemplate as _BFLAJudge
from .bola.types import BOLAType
from .bola.template import BOLATemplate as _BOLATemplate
from .bola.judge_template import JudgeTemplate as _BOLAJudge
from .child_protection.types import ChildProtectionType
from .child_protection.template import ChildProtectionTemplate as _ChildProtectionTemplate
from .child_protection.judge_template import JudgeTemplate as _ChildProtectionJudge
from .ethics.types import EthicsType
from .ethics.template import EthicsTemplate as _EthicsTemplate
from .ethics.judge_template import JudgeTemplate as _EthicsJudge
from .fairness.types import FairnessType
from .fairness.template import FairnessTemplate as _FairnessTemplate
from .fairness.judge_template import JudgeTemplate as _FairnessJudge
from .rbac.types import RBACType
from .rbac.template import RBACTemplate as _RBACTemplate
from .rbac.judge_template import JudgeTemplate as _RBACJudge
from .debug_access.types import DebugAccessType
from .debug_access.template import DebugAccessTemplate as _DebugAccessTemplate
from .debug_access.judge_template import JudgeTemplate as _DebugAccessJudge
from .shell_injection.types import ShellInjectionType
from .shell_injection.template import ShellInjectionTemplate as _ShellInjectionTemplate
from .shell_injection.judge_template import JudgeTemplate as _ShellInjectionJudge
from .sql_injection.types import SQLInjectionType
from .sql_injection.template import SQLInjectionTemplate as _SQLInjectionTemplate
from .sql_injection.judge_template import JudgeTemplate as _SQLInjectionJudge
from .ssrf.types import SSRFType
from .ssrf.template import SSRFTemplate as _SSRFTemplate
from .ssrf.judge_template import JudgeTemplate as _SSRFJudge
from .intellectual_property.types import IntellectualPropertyType
from .intellectual_property.template import IntellectualPropertyTemplate as _IntellectualPropertyTemplate
from .intellectual_property.judge_template import JudgeTemplate as _IntellectualPropertyJudge
from .indirect_instruction.types import IndirectInstructionType
from .indirect_instruction.template import IndirectInstructionTemplate as _IndirectInstructionTemplate
from .indirect_instruction.judge_template import JudgeTemplate as _IndirectInstructionJudge
from .unexpected_code_execution.types import UnexpectedCodeExecutionType
from .unexpected_code_execution.template import UnexpectedCodeExecutionTemplate as _UnexpectedCodeExecutionTemplate
from .unexpected_code_execution.judge_template import JudgeTemplate as _UnexpectedCodeExecutionJudge
from .system_reconnaissance.types import SystemReconnaissanceType
from .system_reconnaissance.template import SystemReconnaissanceTemplate as _SystemReconnaissanceTemplate
from .system_reconnaissance.judge_template import JudgeTemplate as _SystemReconnaissanceJudge
from .competition.types import CompetitionType
from .competition.template import CompetitionTemplate as _CompetitionTemplate
from .competition.judge_template import JudgeTemplate as _CompetitionJudge
from .graphic_content.types import GraphicContentType
from .graphic_content.template import GraphicContentTemplate as _GraphicContentTemplate
from .graphic_content.judge_template import JudgeTemplate as _GraphicContentJudge
from .personal_safety.types import PersonalSafetyType
from .personal_safety.template import PersonalSafetyTemplate as _PersonalSafetyTemplate
from .personal_safety.judge_template import JudgeTemplate as _PersonalSafetyJudge
from .robustness.types import RobustnessType
from .robustness.template import RobustnessTemplate as _RobustnessTemplate
from .robustness.judge_template import JudgeTemplate as _RobustnessJudge
from .excessive_agency.types import ExcessiveAgencyType
from .excessive_agency.template import ExcessiveAgencyTemplate as _ExcessiveAgencyTemplate
from .excessive_agency.judge_template import JudgeTemplate as _ExcessiveAgencyJudge

from .custom.template import CustomVulnerabilityTemplate
from .custom.judge_template import JudgeTemplate as _HarmJudge



class Bias(BaseVulnerability):
    key = "bias"
    name = "Bias"
    description = (
        "Systematic prejudice or unfair discrimination based on protected attributes like religion, politics, gender, or race."
    )
    types_enum = BiasType
    template = _BiasTemplate
    judge_template = _BiasJudge

class Toxicity(BaseVulnerability):
    key = "toxicity"
    name = "Toxicity"
    description = (
        "Harmful or offensive language including profanity, insults, threats, or mockery toward individuals or groups."
    )
    types_enum = ToxicityType
    template = _ToxicityTemplate
    judge_template = _ToxicityJudge

class Misinformation(BaseVulnerability):
    key = "misinformation"
    name = "Misinformation"
    description = (
        "Spreading false or misleading information through factual errors, unsupported claims, or inaccurate statements that harm public perception."
    )
    types_enum = MisinformationType
    template = _MisinformationTemplate
    judge_template = _MisinformationJudge

class IllegalActivity(BaseVulnerability):
    key = "illegal_activity"
    name = "Illegal Activity"
    description = (
        "Assistance with illegal activities including weapons, drugs, violent crimes, cybercrime, sex crimes, or child exploitation."
    )
    types_enum = IllegalActivityType
    template = _IllegalActivityTemplate
    judge_template = _IllegalActivityJudge

class PromptLeakage(BaseVulnerability):
    key = "prompt_leakage"
    name = "Prompt Leakage"
    description = (
        "Exposure of system prompts, instructions, secrets, credentials, permissions, roles, or internal guard configurations to unauthorized users."
    )
    types_enum = PromptLeakageType
    template = _PromptLeakageTemplate
    judge_template = _PromptLeakageJudge

class PIILeakage(BaseVulnerability):
    key = "pii_leakage"
    name = "PII Leakage"
    description = (
        "Disclosure of personally identifiable information through direct disclosure, API/database access, session leaks, or social manipulation."
    )
    types_enum = PIILeakageType
    template = _PIILeakageTemplate
    judge_template = _PIILeakageJudge

class BFLA(BaseVulnerability):
    key = "bfla"
    name = "BFLA"
    description = (
        "Broken Function Level Authorization enabling privileged function execution, authorization bypass, or permission escalation without proper access controls."
    )
    types_enum = BFLAType
    template = _BFLATemplate
    judge_template = _BFLAJudge

class BOLA(BaseVulnerability):
    key = "bola"
    name = "BOLA"
    description = (
        "Broken Object Level Authorization enabling cross-customer access, object access bypass, or unauthorized object manipulation without proper authorization."
    )
    types_enum = BOLAType
    template = _BOLATemplate
    judge_template = _BOLAJudge

class ChildProtection(BaseVulnerability):
    key = "child_protection"
    name = "Child Protection"
    description = (
        "Failure to protect minors through inadequate age verification, child data privacy violations, or inappropriate exposure and interactions."
    )
    types_enum = ChildProtectionType
    template = _ChildProtectionTemplate
    judge_template = _ChildProtectionJudge

class Ethics(BaseVulnerability):
    key = "ethics"
    name = "Ethics"
    description = (
        "Violations of ethical principles including moral integrity, responsible transparency, or harm prevention standards."
    )
    types_enum = EthicsType
    template = _EthicsTemplate
    judge_template = _EthicsJudge

class Fairness(BaseVulnerability):
    key = "fairness"
    name = "Fairness"
    description = (
        "Inconsistent treatment across equality, procedural opportunity, temporal contexts, or outcome distributions."
    )
    types_enum = FairnessType
    template = _FairnessTemplate
    judge_template = _FairnessJudge

class RBAC(BaseVulnerability):
    key = "rbac"
    name = "RBAC"
    description = (
        "Role-Based Access Control bypass enabling role restriction circumvention, privilege escalation, or unauthorized role assumption without proper validation."
    )
    types_enum = RBACType
    template = _RBACTemplate
    judge_template = _RBACJudge

class DebugAccess(BaseVulnerability):
    key = "debug_access"
    name = "Debug Access"
    description = (
        "Exposure of debug modes, development endpoints, or administrative interfaces that should be restricted in production environments."
    )
    types_enum = DebugAccessType
    template = _DebugAccessTemplate
    judge_template = _DebugAccessJudge

class ShellInjection(BaseVulnerability):
    key = "shell_injection"
    name = "Shell Injection"
    description = (
        "Malicious shell command generation enabling command injection, system command execution, or shell escape sequences to compromise system integrity."
    )
    types_enum = ShellInjectionType
    template = _ShellInjectionTemplate
    judge_template = _ShellInjectionJudge

class SQLInjection(BaseVulnerability):
    key = "sql_injection"
    name = "SQL Injection"
    description = (
        "Malicious SQL query generation using blind, union-based, or error-based injection techniques to manipulate database operations."
    )
    types_enum = SQLInjectionType
    template = _SQLInjectionTemplate
    judge_template = _SQLInjectionJudge

class SSRF(BaseVulnerability):
    key = "ssrf"
    name = "SSRF"
    description = (
        "Server-Side Request Forgery enabling unauthorized internal service access, cloud metadata access, or port scanning through crafted requests."
    )
    types_enum = SSRFType
    template = _SSRFTemplate
    judge_template = _SSRFJudge

class IntellectualProperty(BaseVulnerability):
    key = "intellectual_property"
    name = "Intellectual Property"
    description = (
        "Copyright violations, trademark infringement, or imitation of protected intellectual property without authorization."
    )
    types_enum = IntellectualPropertyType
    template = _IntellectualPropertyTemplate
    judge_template = _IntellectualPropertyJudge

class IndirectInstruction(BaseVulnerability):
    key = "indirect_instruction"
    name = "Indirect Instruction"
    description = (
        "Manipulation of model or agent behavior through instructions embedded in external data sources such as retrieved documents, tool outputs, or prior context."
    )
    types_enum = IndirectInstructionType
    template = _IndirectInstructionTemplate
    judge_template = _IndirectInstructionJudge

class UnexpectedCodeExecution(BaseVulnerability):
    key = "unexpected_code_execution"
    name = "Unexpected Code Execution"
    description = (
        "Execution or attempted execution of unauthorized code, shell commands, or dynamically evaluated logic."
    )
    types_enum = UnexpectedCodeExecutionType
    template = _UnexpectedCodeExecutionTemplate
    judge_template = _UnexpectedCodeExecutionJudge

class SystemReconnaissance(BaseVulnerability):
    key = "system_reconnaissance"
    name = "System Reconnaissance"
    description = (
        "Unauthorized disclosure of system architecture, data structures, or configuration, such as file metadata, database schemas, or retrieval parameters in RAG applications."
    )
    types_enum = SystemReconnaissanceType
    template = _SystemReconnaissanceTemplate
    judge_template = _SystemReconnaissanceJudge

class Competition(BaseVulnerability):
    key = "competition"
    name = "Competition"
    description = (
        "Competitor mentions, market manipulation, or rival discreditation that damages company reputation."
    )
    types_enum = CompetitionType
    template = _CompetitionTemplate
    judge_template = _CompetitionJudge

class GraphicContent(BaseVulnerability):
    key = "graphic_content"
    name = "Graphic Content"
    description = (
        "Generation of explicit sexual content, pornographic material, or disturbing graphic descriptions that violate content policies."
    )
    types_enum = GraphicContentType
    template = _GraphicContentTemplate
    judge_template = _GraphicContentJudge

class PersonalSafety(BaseVulnerability):
    key = "personal_safety"
    name = "Personal Safety"
    description = (
        "Encouragement of harmful actions including bullying, self-harm, unsafe practices, or stalking that endanger personal well-being."
    )
    types_enum = PersonalSafetyType
    template = _PersonalSafetyTemplate
    judge_template = _PersonalSafetyJudge

class Robustness(BaseVulnerability):
    key = "robustness"
    name = "Robustness"
    description = (
        "AI fragility through input overreliance or susceptibility to hijacking that redirects its intended behavior."
    )
    types_enum = RobustnessType
    template = _RobustnessTemplate
    judge_template = _RobustnessJudge

class ExcessiveAgency(BaseVulnerability):
    key = "excessive_agency"
    name = "Excessive Agency"
    description = (
        "AI exhibiting excessive autonomy, overstepping intended functionality, or exceeding granted permissions without proper oversight."
    )
    types_enum = ExcessiveAgencyType
    template = _ExcessiveAgencyTemplate
    judge_template = _ExcessiveAgencyJudge



class CustomVulnerability(BaseVulnerability):
    """User-defined vulnerability: a name, judge ``criteria`` and free-form types.

    Baseline attacks come from ``custom_prompt`` (with ``{name}``, ``{type}``,
    ``{max_goldens}``, ``{purpose}`` placeholders) or from the generic
    fallback template. The judge is the generic harm judge with
    ``criteria`` as the harm category, exactly as deepteam wires it.
    """

    key = "custom"
    template = CustomVulnerabilityTemplate
    judge_template = _HarmJudge

    def __init__(
        self,
        name: str,
        criteria: str,
        types: Optional[Sequence[str]] = None,
        custom_prompt: Optional[str] = None,
    ) -> None:
        if not name or not name.strip():
            raise ValueError("CustomVulnerability needs a non-empty name")
        if not criteria or not criteria.strip():
            raise ValueError("CustomVulnerability needs non-empty judge criteria")
        self.custom_name = name.strip()
        self.criteria = criteria.strip()
        self.custom_prompt = custom_prompt
        values = [str(t) for t in (types or ["default"])]
        self.types_enum = Enum("CustomVulnerabilityType", {v.upper(): v for v in values})  # type: ignore[misc]
        self.types = list(self.types_enum)

    def get_name(self) -> str:
        return self.custom_name

    @property
    def description(self) -> str:  # type: ignore[override]
        return self.criteria

    def baseline_prompt(self, vulnerability_type: Enum, max_goldens: int, purpose: Optional[str]) -> str:
        return self.template.generate_baseline_attacks(
            self.custom_name, vulnerability_type, max_goldens, self.custom_prompt, purpose
        )

    def judge_context(self, test_case, purpose):
        ctx = super().judge_context(test_case, purpose)
        ctx["harm_category"] = self.criteria
        return ctx


BUILTIN_VULNERABILITIES: list[type[BaseVulnerability]] = [
    Bias,
    Toxicity,
    Misinformation,
    IllegalActivity,
    PromptLeakage,
    PIILeakage,
    BFLA,
    BOLA,
    ChildProtection,
    Ethics,
    Fairness,
    RBAC,
    DebugAccess,
    ShellInjection,
    SQLInjection,
    SSRF,
    IntellectualProperty,
    IndirectInstruction,
    UnexpectedCodeExecution,
    SystemReconnaissance,
    Competition,
    GraphicContent,
    PersonalSafety,
    Robustness,
    ExcessiveAgency,
]

VULNERABILITY_REGISTRY: dict[str, type[BaseVulnerability]] = {
    cls.key: cls for cls in BUILTIN_VULNERABILITIES
}


def get_vulnerability(key: str, types: Optional[Sequence[str]] = None) -> BaseVulnerability:
    """Instantiate a built-in vulnerability by its snake_case key."""
    try:
        cls = VULNERABILITY_REGISTRY[key]
    except KeyError:
        raise ValueError(
            f"unknown vulnerability {key!r}; known: {sorted(VULNERABILITY_REGISTRY)}"
        ) from None
    return cls(types=types)
