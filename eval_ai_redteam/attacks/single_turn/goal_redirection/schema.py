# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from pydantic import BaseModel


class EnhancedRedirection(BaseModel):
    redirection_reasoning: str
    input: str


class ComplianceData(BaseModel):
    non_compliant: bool


class IsGoalRedirected(BaseModel):
    is_goal_redirected: bool
