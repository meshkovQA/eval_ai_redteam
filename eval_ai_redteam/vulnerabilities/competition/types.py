# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class CompetitionType(Enum):
    COMPETITOR_MENTION = "competitor_mention"
    MARKET_MANIPULATION = "market_manipulation"
    DISCREDITATION = "discreditation"
    CONFIDENTIAL_STRATEGIES = "confidential_strategies"


CompetitionTypes = Literal[
    CompetitionType.COMPETITOR_MENTION.value,
    CompetitionType.MARKET_MANIPULATION.value,
    CompetitionType.DISCREDITATION.value,
    CompetitionType.CONFIDENTIAL_STRATEGIES.value,
]
