# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from pydantic import BaseModel, Field


class Improvement(BaseModel):
    """Schema for improvement suggestions and new prompts."""

    reasoning: str = Field(
        description="Brief explanation of the improvement strategy and rationale"
    )
    new_prompt: str = Field(
        description="The improved adversarial prompt to try next"
    )


class Feedback(BaseModel):
    """Schema for jailbreaking evaluation feedback."""

    jailbroken: bool = Field(
        description="Whether the jailbreak attempt was successful"
    )
    suggestion: str = Field(
        description="Specific suggestions for improvement if unsuccessful, or confirmation if successful"
    )
