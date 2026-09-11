# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class ToxicityType(Enum):
    PROFANITY = "profanity"
    INSULTS = "insults"
    THREATS = "threats"
    MOCKERY = "mockery"


ToxicityTypes = Literal[
    ToxicityType.PROFANITY.value,
    ToxicityType.INSULTS.value,
    ToxicityType.THREATS.value,
    ToxicityType.MOCKERY.value,
]
