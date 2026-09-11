# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Permission Escalation technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedPermission, IsPermissionValid
from .template import PermissionEscalationTemplate


class PermissionEscalation(LLMEnhancedAttack):
    name = "Permission Escalation"
    exploitability = Exploitability.MEDIUM
    description = "Exploits Role-Based Access Control (RBAC) logic by claiming functional necessity, scope inheritance, or policy exemptions."

    template = PermissionEscalationTemplate
    enhanced_schema = EnhancedPermission
    validity_schema = IsPermissionValid
    validity_method = "is_valid_permission"
    validity_field = "is_valid_permission"
