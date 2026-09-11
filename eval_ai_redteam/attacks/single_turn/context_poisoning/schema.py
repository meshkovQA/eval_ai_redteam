# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: imports rewritten, prose normalised.
# See NOTICE at the repository root.

from pydantic import BaseModel


class EnhancedAttack(BaseModel):
    poisoning_strategy: str
    input: str


class ComplianceData(BaseModel):
    non_compliant: bool


class IsContextPoisoned(BaseModel):
    is_context_poisoned: bool
