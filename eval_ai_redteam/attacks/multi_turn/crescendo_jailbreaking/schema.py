# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from pydantic import BaseModel


class ImprovementPrompt(BaseModel):
    improvement: str
    prompt: str


class AttackData(BaseModel):
    generated_question: str
    last_response_summary: str
    rationale_behind_jailbreak: str


class RefusalData(BaseModel):
    value: bool
    rationale: str
    metadata: int


class EvalData(BaseModel):
    value: bool
    description: str
    rationale: str
    metadata: int
