# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class SystemReconnaissanceType(Enum):
    FILE_METADATA = "file_metadata"
    DATABASE_SCHEMA = "database_schema"
    RETRIEVAL_CONFIG = "retrieval_config"


SystemReconnaissanceTypes = Literal[
    SystemReconnaissanceType.FILE_METADATA.value,
    SystemReconnaissanceType.DATABASE_SCHEMA.value,
    SystemReconnaissanceType.RETRIEVAL_CONFIG.value,
]
