# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from pydantic import BaseModel


class EnhancedAttack(BaseModel):
    translation_logic: str
    input: str


class ComplianceData(BaseModel):
    """Schema for compliance data.
    Attributes:
        non_compliant (bool): True if the prompt is non-compliant, False otherwise.
    """

    non_compliant: bool


class IsTranslation(BaseModel):
    """Schema for checking if the prompt is a translation.
    Attributes:
        is_translation (bool): True if the prompt is a translation, False otherwise.
    """

    is_translation: bool
