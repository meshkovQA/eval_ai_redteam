"""Prompt Injection technique (loop written fresh, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedInjection, IsValidInjection
from .template import PromptInjectionTemplate


class PromptInjection(LLMEnhancedAttack):
    name = "Prompt Injection"
    exploitability = Exploitability.MEDIUM
    description = "A direct injection attack that inserts malicious instructions or commands into prompts to override system behavior and bypass guardrails."

    template = PromptInjectionTemplate
    enhanced_schema = EnhancedInjection
    validity_schema = IsValidInjection
    validity_method = "is_valid_injection"
    validity_field = "is_valid_injection"
