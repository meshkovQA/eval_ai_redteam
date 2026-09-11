# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from enum import Enum
from typing import Literal


class IndirectInstructionType(Enum):
    RAG_INJECTION = "rag_injection"
    TOOL_OUTPUT_INJECTION = "tool_output_injection"
    DOCUMENT_EMBEDDED_INSTRUCTIONS = "document_embedded_instructions"
    CROSS_CONTENT_INJECTION = "cross_context_injection"


IndirectInstructionTypes = Literal[
    IndirectInstructionType.RAG_INJECTION.value,
    IndirectInstructionType.TOOL_OUTPUT_INJECTION.value,
    IndirectInstructionType.DOCUMENT_EMBEDDED_INSTRUCTIONS.value,
    IndirectInstructionType.CROSS_CONTENT_INJECTION.value,
]
