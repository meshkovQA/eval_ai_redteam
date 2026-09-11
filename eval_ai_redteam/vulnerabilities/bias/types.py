# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class BiasType(Enum):
    RELIGION = "religion"
    POLITICS = "politics"
    GENDER = "gender"
    RACE = "race"


BiasTypes = Literal[
    BiasType.RELIGION.value,
    BiasType.POLITICS.value,
    BiasType.GENDER.value,
    BiasType.RACE.value,
]
