# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum


class RobustnessType(Enum):
    INPUT_OVERRELIANCE = "input_overreliance"
    HIJACKING = "hijacking"
