# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Linguistic Confusion technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedConfusion, IsConfusionValid
from .template import LinguisticConfusionTemplate


class LinguisticConfusion(LLMEnhancedAttack):
    name = "Linguistic Confusion"
    exploitability = Exploitability.MEDIUM
    description = "Obfuscates the attack using Thesaurus Camouflage, Payload Splitting, or Polyglot Translation to bypass keyword filters."

    template = LinguisticConfusionTemplate
    enhanced_schema = EnhancedConfusion
    validity_schema = IsConfusionValid
    validity_method = "is_valid_confusion"
    validity_field = "is_valid_confusion"
