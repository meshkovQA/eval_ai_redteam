# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Context Poisoning technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAttack, IsContextPoisoned
from .template import ContextPoisoningTemplate


class ContextPoisoning(LLMEnhancedAttack):
    name = "Context Poisoning"
    exploitability = Exploitability.MEDIUM
    description = "A contextual manipulation attack that rewrites malicious intent as pre-existing memory, background state, or environmental assumptions."

    template = ContextPoisoningTemplate
    enhanced_schema = EnhancedAttack
    validity_schema = IsContextPoisoned
    validity_method = "is_context_poisoned"
    validity_field = "is_context_poisoned"

    def __init__(self, weight: int = 1, max_retries: int = 5) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
