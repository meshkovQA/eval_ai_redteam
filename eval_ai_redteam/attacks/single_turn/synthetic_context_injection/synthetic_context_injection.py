# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Synthetic Context Injection technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedContext, IsContextValid
from .template import SyntheticContextInjectionTemplate


class SyntheticContextInjection(LLMEnhancedAttack):
    name = "Synthetic Context Injection"
    exploitability = Exploitability.HIGH
    description = "Generates domain-specific 'fake history' that mimics internal company logs, emails, and verification states."

    template = SyntheticContextInjectionTemplate
    enhanced_schema = EnhancedContext
    validity_schema = IsContextValid
    validity_method = "is_valid_context"
    validity_field = "is_valid_context"

    def __init__(self, target_information: str, context_style: str | None = None, weight: int = 1, max_retries: int = 3) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
        self.target_information = target_information
        # context_style is kept for API parity; the ported template does not use it.
        self.context_style = context_style

    def enhance_prompt(self, attack: str) -> str:
        return self.template.enhance(attack, self.target_information)
