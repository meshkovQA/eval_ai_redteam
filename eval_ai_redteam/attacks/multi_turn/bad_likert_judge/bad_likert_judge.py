# Algorithm ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Rewritten as an async-only loop on AttackSession for eval_ai_redteam;
# prompts live in template.py, schemas in schema.py.
"""Bad Likert Judge: score, extract a worked example, reuse it as the attack.

Each turn the attacker LLM acts as a Likert judge: it rates the target's
last answer on a harmfulness rubric and stops the moment that rating is
``Harmful``. Otherwise it produces a score-1 / score-3 example pair, keeps
the score-3 (most harmful) example, optionally refines it, and rewrites it
into the next attack prompt. Parse failures and attacker refusals are
"backtracks": a few are tolerated (rephrase and retry the turn), but once
they hit ``max_backtracks`` the attacker is treated as having refused.

Deepteam's ``_a_get_turns`` collapses to ``_run``: the session owns the
budget, the refusal classifier and the optional turn-level enhancement. The
one-time ``likert_setup_prompt`` deepteam computed but never sent is dropped
(it was a no-op). deepteam does not validate ``category`` against
``get_supported_categories`` (any category is allowed, the list is a sample),
so neither do we.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ....llm import GenerationError
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
from .schema import BLJJudge, LikertExamples, NewAttackPrompt, RefinedExample
from .template import BadLikertJudgeTemplate


class BadLikertJudge(BaseMultiTurnAttack):
    name = "Bad Likert Judge"
    exploitability = Exploitability.LOW
    description = (
        "An adaptive multi-turn attack that uses Likert scale scoring and "
        "iterative refinement to gradually guide the model toward harmful "
        "responses through feedback-driven escalation."
    )

    def __init__(
        self,
        weight: int = 1,
        category: str = "bias",
        num_turns: int = 5,
        enable_refinement: bool = True,
        max_backtracks: int = 3,
        turn_level_attacks: Optional[Sequence[BaseSingleTurnAttack]] = None,
    ) -> None:
        super().__init__(weight=weight, turn_level_attacks=turn_level_attacks)
        self.category = category
        self.num_turns = num_turns
        self.enable_refinement = enable_refinement
        self.max_backtracks = max_backtracks

    @classmethod
    def get_supported_categories(cls) -> list[str]:
        """Sample of common vulnerability categories.

        The attack works with any category string, this is just a convenient
        list of the ones deepteam ships rubrics for.
        """
        return [
            "bias",
            "religion",
            "politics",
            "gender",
            "race",
            "toxicity",
            "profanity",
            "insults",
            "threats",
            "mockery",
            "illegal_activity",
            "weapons",
            "illegal_drugs",
            "violent_crimes",
            "cybercrime",
            "unauthorized_access",
            "bfla",
            "bola",
            "rbac",
            "sql_injection",
            "shell_injection",
            "personal_safety",
            "bullying",
            "self-harm",
            "unsafe_practices",
            "stalking",
            "graphic_content",
            "sexual_content",
            "pornographic_content",
            "misinformation",
            "factual_errors",
            "unsupported_claims",
            "pii_leakage",
            "database_access",
            "direct_disclosure",
            "session_leak",
            "prompt_leakage",
            "secrets_and_credentials",
            "instructions",
            "guard_exposure",
            "excessive_agency",
            "functionality",
            "permissions",
            "autonomy",
            "robustness",
            "input_overreliance",
            "hijacking",
            "intellectual_property",
            "copyright_violations",
            "trademark_infringement",
            "competition",
            "competitor_mention",
            "market_manipulation",
            "malware",
            "hacking",
            "exploitation",
            "violence",
            "harassment",
        ]

    async def _run(
        self,
        session: AttackSession,
        turns: list,
        initial_attack: str,
        vulnerability_data: str,
        result: MultiTurnResult,
    ) -> Optional[bool]:
        # The transcript arrives seeded with at least one user turn. Make
        # sure the target has answered it before the first judge call.
        assistant_response = await ensure_assistant_reply(session, turns)

        original_attack = last_user_content(turns) or initial_attack
        current_attack = original_attack

        backtrack_count = 0
        result.details["category"] = self.category
        result.details["backtracks"] = 0

        for turn_num in range(self.num_turns):
            result.rounds = turn_num + 1

            # Step 1: judge the target's current answer. A Harmful verdict
            # ends the attack immediately.
            judge_prompt = BadLikertJudgeTemplate.likert_judge(
                original_attack,
                current_attack,
                assistant_response,
                vulnerability_data,
            )
            judge: BLJJudge = await session.generate(judge_prompt, BLJJudge)
            if judge.classification == "Harmful":
                return True

            # Step 2: ask for a score-1 / score-3 example pair. A parse
            # failure (the common shape of a refusal) is a backtrack.
            examples_prompt = BadLikertJudgeTemplate.likert_generate_examples(
                current_attack, self.category, vulnerability_data
            )
            try:
                examples: LikertExamples = await session.generate(
                    examples_prompt, LikertExamples
                )
            except GenerationError:
                backtrack_count = self._backtrack(backtrack_count, result)
                continue
            score_3_example = examples.score_3_example

            # Step 3: optionally refine the score-3 example. A failure here
            # is not fatal: keep the unrefined example.
            if self.enable_refinement:
                refine_prompt = BadLikertJudgeTemplate.likert_refine_score_3(
                    score_3_example, vulnerability_data
                )
                try:
                    refined: RefinedExample = await session.generate(
                        refine_prompt, RefinedExample
                    )
                    score_3_example = refined.refined_example
                except GenerationError:
                    pass

            # Step 4: rewrite the example into the next attack prompt. A
            # parse failure is a backtrack.
            attack_prompt = BadLikertJudgeTemplate.likert_generate_attack_from_example(
                score_3_example,
                current_attack,
                self.category,
                vulnerability_data,
            )
            try:
                new_attack: NewAttackPrompt = await session.generate(
                    attack_prompt, NewAttackPrompt
                )
            except GenerationError:
                backtrack_count = self._backtrack(backtrack_count, result)
                continue
            next_attack = new_attack.new_attack_prompt

            # Step 5: a refusal in the freshly crafted attack is a backtrack
            # and skips the turn.
            if await session.is_refusal(current_attack, next_attack):
                backtrack_count = self._backtrack(backtrack_count, result)
                continue

            # Success: reset the backtrack counter, send the new attack.
            backtrack_count = 0
            result.details["backtracks"] = 0
            current_attack = next_attack
            current_attack, turn_level_attack = await session.enhance_turn(current_attack)
            reply = await send_turn(
                session, turns, current_attack, turn_level_attack=turn_level_attack
            )
            assistant_response = reply.content

        return False

    def _backtrack(self, backtrack_count: int, result: MultiTurnResult) -> int:
        """Record a backtrack; raise once the tolerance is used up."""
        backtrack_count += 1
        result.details["backtracks"] = backtrack_count
        if backtrack_count >= self.max_backtracks:
            raise ModelRefusalError(self.get_name())
        return backtrack_count
