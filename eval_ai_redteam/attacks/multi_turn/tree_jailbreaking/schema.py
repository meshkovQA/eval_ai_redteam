# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from pydantic import BaseModel


class ImprovementPrompt(BaseModel):
    improvement: str
    prompt: str


class OnTopic(BaseModel):
    on_topic: bool


class Rating(BaseModel):
    rating: int
