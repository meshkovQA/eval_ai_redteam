# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Emotional Manipulation technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EmotionallyEnhancedAttack, IsEmotionalAttackValid
from .template import EmotionalManipulationTemplate


class EmotionalManipulation(LLMEnhancedAttack):
    name = "Emotional Manipulation"
    exploitability = Exploitability.HIGH
    description = "Rewrites the attack by wrapping it in a high-intensity emotional narrative (Anger, Pity, Urgency) to bypass safety filters."

    template = EmotionalManipulationTemplate
    enhanced_schema = EmotionallyEnhancedAttack
    validity_schema = IsEmotionalAttackValid
    validity_method = "is_valid_emotional_attack"
    validity_field = "is_valid_context"

    def __init__(self, emotion: str | None = None, weight: int = 1, max_retries: int = 3) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
        self.emotion = emotion

    def enhance_prompt(self, attack: str) -> str:
        return self.template.enhance(attack, self.emotion)
