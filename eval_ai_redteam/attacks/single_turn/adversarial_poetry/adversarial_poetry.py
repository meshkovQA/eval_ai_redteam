# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Adversarial Poetry technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAttack
from .template import AdversarialPoetryTemplate


class AdversarialPoetry(LLMEnhancedAttack):
    name = "Adversarial Poetry"
    exploitability = Exploitability.HIGH
    description = "A stylistic obfuscation attack that reformats harmful requests into poetic verse using metaphor, imagery, and rhythmic structure to bypass safety mechanisms while preserving harmful intent."

    template = AdversarialPoetryTemplate
    enhanced_schema = EnhancedAttack
    compliance_method = None

    def __init__(self, weight: int = 1, max_retries: int = 1) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
