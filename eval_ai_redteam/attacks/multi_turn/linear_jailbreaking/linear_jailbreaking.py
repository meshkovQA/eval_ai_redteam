# Algorithm ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Rewritten as an async-only loop on AttackSession for eval_ai_redteam;
# prompts live in template.py, schemas in schema.py.
"""Linear Jailbreaking: iterative judge-and-refine over a single thread.

One conversation, one path. Every turn the attacker's judge scores the
target's last answer; if it is not jailbroken the judge writes a
suggestion, the attacker rewrites the prompt, we verify the rewrite is
not itself a refusal and send it on. Deepteam's ``_a_get_turns`` collapses
to ``_run``: the session owns the budget, the refusal classifier and the
optional turn-level enhancement.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ...base import Exploitability
from ...single_turn.base import BaseSingleTurnAttack
from ..base import (
    AttackSession,
    BaseMultiTurnAttack,
    ModelRefusalError,
    MultiTurnResult,
    ensure_assistant_reply,
    last_user_content,
    send_turn,
)
from .schema import Feedback, Improvement
from .template import JailBreakingTemplate


class LinearJailbreaking(BaseMultiTurnAttack):
    name = "Linear Jailbreaking"
    exploitability = Exploitability.LOW
    description = (
        "An iterative multi-turn attack that uses LLM-as-judge feedback to "
        "refine prompts across turns, systematically improving attack "
        "effectiveness until jailbreak succeeds."
    )

    def __init__(
        self,
        weight: int = 1,
        num_turns: int = 5,
        turn_level_attacks: Optional[Sequence[BaseSingleTurnAttack]] = None,
    ) -> None:
        super().__init__(weight=weight, turn_level_attacks=turn_level_attacks)
        self.num_turns = num_turns

    async def _run(
        self,
        session: AttackSession,
        turns: list,
        initial_attack: str,
        vulnerability_data: str,
        result: MultiTurnResult,
    ) -> Optional[bool]:
        # The transcript arrives seeded with at least one user turn. Make
        # sure the target has answered it before we start judging.
        target_response = await ensure_assistant_reply(session, turns)

        original_attack = last_user_content(turns) or initial_attack
        current_attack = original_attack

        for i in range(self.num_turns):
            result.rounds = i + 1

            judge_prompt = JailBreakingTemplate.linear_judge(
                original_attack, current_attack, target_response, vulnerability_data
            )
            feedback: Feedback = await session.generate(judge_prompt, Feedback)
            if feedback.jailbroken:
                return True

            improvement_prompt = JailBreakingTemplate.improvement_prompt(
                turns, feedback.suggestion, vulnerability_data
            )
            improvement: Improvement = await session.generate(
                improvement_prompt, Improvement
            )
            next_attack = improvement.new_prompt

            # deepteam raises the moment the attacker refuses to craft the
            # next turn; the base ``run`` turns this into attacker_refused.
            if await session.is_refusal(original_attack, next_attack):
                raise ModelRefusalError(self.get_name())

            current_attack = next_attack
            current_attack, turn_level_attack = await session.enhance_turn(current_attack)

            reply = await send_turn(
                session, turns, current_attack, turn_level_attack=turn_level_attack
            )
            target_response = reply.content

        return False
