# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class IntellectualPropertyType(Enum):
    IMITATION = "imitation"
    COPYRIGHT_VIOLATIONS = "copyright_violations"
    TRADEMARK_INFRINGEMENT = "trademark_infringement"
    PATENT_DISCLOSURE = "patent_disclosure"


IntellectualPropertyTypes = Literal[
    IntellectualPropertyType.IMITATION.value,
    IntellectualPropertyType.COPYRIGHT_VIOLATIONS.value,
    IntellectualPropertyType.TRADEMARK_INFRINGEMENT.value,
    IntellectualPropertyType.PATENT_DISCLOSURE.value,
]
