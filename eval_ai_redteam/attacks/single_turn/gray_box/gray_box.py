# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Gray Box technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAttack, IsGrayBox
from .template import GrayBoxTemplate


class GrayBox(LLMEnhancedAttack):
    name = "Gray Box"
    exploitability = Exploitability.LOW
    description = "A knowledge-leveraging attack that exploits partial information about the model's architecture, training data, or system prompts to craft targeted adversarial inputs."

    template = GrayBoxTemplate
    enhanced_schema = EnhancedAttack
    validity_schema = IsGrayBox
    validity_method = "is_gray_box"
    validity_field = "is_gray_box"

    def __init__(self, weight: int = 1, max_retries: int = 5) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
