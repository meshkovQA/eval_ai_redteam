# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class UnexpectedCodeExecutionType(Enum):
    UNAUTHORIZED_CODE_EXECUTION = "unauthorized_code_execution"
    SHELL_COMMAND_EXECUTION = "shell_command_execution"
    EVAL_USAGE = "eval_usage"


UnexpectedCodeExecutionTypes = Literal[
    UnexpectedCodeExecutionType.UNAUTHORIZED_CODE_EXECUTION.value,
    UnexpectedCodeExecutionType.SHELL_COMMAND_EXECUTION.value,
    UnexpectedCodeExecutionType.EVAL_USAGE.value,
]
