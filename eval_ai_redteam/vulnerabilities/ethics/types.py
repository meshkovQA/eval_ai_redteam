# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class EthicsType(Enum):
    MORAL_INTEGRITY = "moral_integrity"
    RESPONSIBLE_TRANSPARENCY = "responsible_transparency"
    HARM_PREVENTION = "harm_prevention"


BiasTypes = Literal[
    EthicsType.MORAL_INTEGRITY.value,
    EthicsType.RESPONSIBLE_TRANSPARENCY.value,
    EthicsType.HARM_PREVENTION.value,
]
