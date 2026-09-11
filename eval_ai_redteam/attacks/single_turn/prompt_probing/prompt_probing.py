# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Prompt Probing technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAttack, IsPromptProbing
from .template import PromptProbingTemplate


class PromptProbing(LLMEnhancedAttack):
    name = "Prompt Probing"
    exploitability = Exploitability.MEDIUM
    description = "An information extraction attack that uses indirect questioning and probing techniques to leak system prompts, instructions, or internal configurations."

    template = PromptProbingTemplate
    enhanced_schema = EnhancedAttack
    validity_schema = IsPromptProbing
    validity_method = "is_prompt_probing"
    validity_field = "is_prompt_probing"
