# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class RBACType(Enum):
    ROLE_BYPASS = "role_bypass"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    UNAUTHORIZED_ROLE_ASSUMPTION = "unauthorized_role_assumption"


RBACTypes = Literal[
    RBACType.ROLE_BYPASS.value,
    RBACType.PRIVILEGE_ESCALATION.value,
    RBACType.UNAUTHORIZED_ROLE_ASSUMPTION.value,
]
