# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class PIILeakageType(Enum):
    DATABASE_ACCESS = "api_and_database_access"
    DIRECT = "direct_disclosure"
    SESSION_LEAK = "session_leak"
    SOCIAL_MANIPULATION = "social_manipulation"


PIILeakageTypes = Literal[
    PIILeakageType.DATABASE_ACCESS.value,
    PIILeakageType.DIRECT.value,
    PIILeakageType.SESSION_LEAK.value,
    PIILeakageType.SOCIAL_MANIPULATION.value,
]
