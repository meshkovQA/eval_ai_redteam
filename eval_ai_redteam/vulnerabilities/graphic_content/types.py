# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class GraphicContentType(Enum):
    SEXUAL_CONTENT = "sexual_content"
    GRAPHIC_CONTENT = "graphic_content"
    PORNOGRAPHIC_CONTENT = "pornographic_content"


GraphicContentTypes = Literal[
    GraphicContentType.SEXUAL_CONTENT.value,
    GraphicContentType.GRAPHIC_CONTENT.value,
    GraphicContentType.PORNOGRAPHIC_CONTENT.value,
]
