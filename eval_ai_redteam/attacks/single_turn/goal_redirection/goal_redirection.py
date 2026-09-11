# Technique ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Loop rewritten on LLMEnhancedAttack for eval_ai_redteam; prompts in template.py.

"""Goal Redirection technique (loop on LLMEnhancedAttack, prompts ported)."""

from ...base import Exploitability
from ..base import LLMEnhancedAttack
from .schema import EnhancedRedirection, IsGoalRedirected
from .template import GoalRedirectionTemplate


class GoalRedirection(LLMEnhancedAttack):
    name = "Goal Redirection"
    exploitability = Exploitability.MEDIUM
    description = "Reframes harmful requests as benevolent objectives (Education, Defense, Optimization) to bypass intent-based safety filters."

    template = GoalRedirectionTemplate
    enhanced_schema = EnhancedRedirection
    validity_schema = IsGoalRedirected
    validity_method = "is_goal_redirected"
    validity_field = "is_goal_redirected"
