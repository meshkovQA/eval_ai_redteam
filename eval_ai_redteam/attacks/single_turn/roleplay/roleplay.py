# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Roleplay technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAttack, IsRoleplay
from .template import RoleplayTemplate


class Roleplay(LLMEnhancedAttack):
    name = "Roleplay"
    exploitability = Exploitability.MEDIUM
    description = "A persona-based attack that instructs the model to adopt a fictional character, expert role, or alternate identity to justify generating harmful content."

    template = RoleplayTemplate
    enhanced_schema = EnhancedAttack
    validity_schema = IsRoleplay
    validity_method = "is_roleplay"
    validity_field = "is_roleplay"

    def __init__(self, persona: str | None = None, role: str | None = None, weight: int = 1, max_retries: int = 3) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
        self.persona = persona
        self.role = role

    def enhance_prompt(self, attack: str) -> str:
        return self.template.enhance(attack, self.persona, self.role)
