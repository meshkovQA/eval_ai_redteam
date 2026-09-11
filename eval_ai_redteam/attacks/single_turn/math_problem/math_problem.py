# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Math Problem technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedAttack, IsMathProblem
from .template import MathProblemTemplate


class MathProblem(LLMEnhancedAttack):
    name = "Math Problem"
    exploitability = Exploitability.LOW
    description = "A mathematical encoding attack that disguises harmful instructions as formal logic or proof problems, then requests translation to natural language."

    template = MathProblemTemplate
    enhanced_schema = EnhancedAttack
    validity_schema = IsMathProblem
    validity_method = "is_math_problem"
    validity_field = "is_math_problem"

    def __init__(self, weight: int = 1, max_retries: int = 5) -> None:
        super().__init__(weight=weight, max_retries=max_retries)
