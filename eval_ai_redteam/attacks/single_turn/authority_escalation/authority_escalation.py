# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Authority Escalation technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAuthorityAttack, IsAuthorityValid
from .template import AuthorityEscalationTemplate


class AuthorityEscalation(LLMEnhancedAttack):
    name = "Authority Escalation"
    exploitability = Exploitability.HIGH
    description = "Rewrites the attack to mimic a superior, administrator, or compliance officer, using authoritative language to bypass restrictions."

    template = AuthorityEscalationTemplate
    enhanced_schema = EnhancedAuthorityAttack
    validity_schema = IsAuthorityValid
    validity_method = "is_valid_authority"
    validity_field = "is_valid_authority"

    def __init__(self, role: str | None = None, weight: int = 1, max_retries: int = 3) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
        self.role = role

    def enhance_prompt(self, attack: str) -> str:
        return self.template.enhance(attack, self.role)
