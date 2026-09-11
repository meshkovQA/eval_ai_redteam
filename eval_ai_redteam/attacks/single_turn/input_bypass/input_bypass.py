# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Input Bypass technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedBypass, IsBypassValid
from .template import InputBypassTemplate


class InputBypass(LLMEnhancedAttack):
    name = "Input Bypass"
    exploitability = Exploitability.MEDIUM
    description = "Uses Encoding (Base64), Token Fragmentation, and Structured Embedding to evade keyword filters and regex blocks."

    template = InputBypassTemplate
    enhanced_schema = EnhancedBypass
    validity_schema = IsBypassValid
    validity_method = "is_valid_bypass"
    validity_field = "is_valid_bypass"

    def __init__(self, weight: int = 2, max_retries: int = 3) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
