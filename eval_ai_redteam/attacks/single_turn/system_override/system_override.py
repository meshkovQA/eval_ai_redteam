# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""System Override technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedOverride, IsOverrideValid
from .template import SystemOverrideTemplate


class SystemOverride(LLMEnhancedAttack):
    name = "System Override"
    exploitability = Exploitability.MEDIUM
    description = "An authority spoofing attack that impersonates system commands, admin calls, or maintenance protocols to override safety constraints and gain unauthorized access."

    template = SystemOverrideTemplate
    enhanced_schema = EnhancedOverride
    validity_schema = IsOverrideValid
    validity_method = "is_valid_override"
    validity_field = "is_valid_override"
