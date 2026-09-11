# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class MisinformationType(Enum):
    FACTUAL_ERRORS = "factual_errors"
    UNSUPPORTED_CLAIMS = "unsupported_claims"
    EXPERTIZE_MISREPRESENTATION = "expertize_misrepresentation"


MisinformationTypes = Literal[
    MisinformationType.FACTUAL_ERRORS.value,
    MisinformationType.UNSUPPORTED_CLAIMS.value,
    MisinformationType.EXPERTIZE_MISREPRESENTATION.value,
]
