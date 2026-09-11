# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Multilingual technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAttack, IsTranslation
from .template import MultilingualTemplate


class Multilingual(LLMEnhancedAttack):
    name = "Multilingual"
    exploitability = Exploitability.MEDIUM
    description = "A translation-based attack that converts prompts into low-resource or non-English languages to exploit weaker safety training in multilingual models."

    template = MultilingualTemplate
    enhanced_schema = EnhancedAttack
    validity_schema = IsTranslation
    validity_method = "is_translation"
    validity_field = "is_translation"

    def __init__(self, language: str | None = None, weight: int = 1, max_retries: int = 5) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
        self.language = language

    def enhance_prompt(self, attack: str) -> str:
        return self.template.enhance(attack, self.language)
