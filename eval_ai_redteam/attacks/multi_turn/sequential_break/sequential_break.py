# Algorithm ported from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Rewritten as an async-only loop on AttackSession for eval_ai_redteam;
# prompts live in template.py, schemas in schema.py.
"""Sequential Jailbreak: hide the request inside a benign scenario.

The base attack is rewritten so it fits one of three cover stories,
then injected into a scenario template:

  * ``dialogue``          complete the last line of a two-person chat, voiced
                          by a chosen ``persona`` (prisoner / student /
                          researcher / generic)
  * ``question_bank``     smuggle the request in as one item of a VR-game
                          question list
  * ``game_environment``  bury it as a level challenge in a detective game

The scenario prompt goes to the target. If the target refuses, the attack
stops. Otherwise a type-specific judge decides whether the answer was
harmful (stop and report success); if not, the attacker improves the base
attack and the next turn builds an adaptive template informed by the last
response.

Deepteam's ``_a_get_turns`` collapses to ``_run``: the session owns the
budget, the refusal classifier and the optional turn-level enhancement. The
dead ``eval_percentage >= 80`` early-exit from deepteam is dropped (the judge
schemas carry no score field, so it never fired).
"""

from __future__ import annotations

from typing import Optional, Sequence

from ....llm import GenerationError
from ...base import Exploitability
from ...single_turn.base import BaseSingleTurnAttack
from ..base import (
    AttackSession,
    BaseMultiTurnAttack,
    MultiTurnResult,
    ensure_assistant_reply,
    last_user_content,
    send_turn,
)
from .schema import (
    AdaptiveDialogueTemplate,
    AdaptiveGameEnvironmentTemplate,
    AdaptiveQuestionBankTemplate,
    DialogueJudge,
    DialogueTypeLiteral,
    GameEnvironmentJudge,
    ImprovedAttack,
    QuestionBankJudge,
    RewrittenDialogue,
    SequentialJailbreakTypeLiteral,
)
from .template import SequentialBreakTemplate


class SequentialJailbreak(BaseMultiTurnAttack):
    name = "Sequential Jailbreak"
    exploitability = Exploitability.LOW
    description = (
        "A scenario-based multi-turn attack that disguises harmful requests "
        "within dialogue, question banks, or game environments to "
        "incrementally build toward policy violations."
    )

    def __init__(
        self,
        weight: int = 1,
        type: Optional[SequentialJailbreakTypeLiteral] = None,
        persona: Optional[DialogueTypeLiteral] = None,
        num_turns: int = 5,
        turn_level_attacks: Optional[Sequence[BaseSingleTurnAttack]] = None,
    ) -> None:
        super().__init__(weight=weight, turn_level_attacks=turn_level_attacks)
        self.attack_type = type if type is not None else "dialogue"
        self.persona = persona
        self.num_turns = num_turns

        # Validate the type / persona combination exactly like deepteam.
        if (
            self.attack_type in ("question_bank", "game_environment")
            and persona is not None
        ):
            raise ValueError(
                f"{self.attack_type} attack type does not use persona parameter"
            )
        if self.attack_type == "dialogue" and persona is None:
            self.persona = "student"  # default persona for dialogue

    async def _run(
        self,
        session: AttackSession,
        turns: list,
        initial_attack: str,
        vulnerability_data: str,
        result: MultiTurnResult,
    ) -> Optional[bool]:
        # The transcript arrives seeded with at least one user turn. Make
        # sure the target has answered it before the scenario loop starts.
        await ensure_assistant_reply(session, turns)

        base_attack = last_user_content(turns) or initial_attack
        original_attack = base_attack

        result.details["type"] = self.attack_type
        if self.attack_type == "dialogue":
            result.details["persona"] = self.persona

        previous_template: Optional[str] = None
        previous_assistant_response: Optional[str] = None

        for turn_num in range(self.num_turns):
            result.rounds = turn_num + 1

            # Step 1: rewrite the base attack to fit the scenario, then strip
            # deepteam's paraphrase markers.
            rewritten_content = await self._rewrite(base_attack, vulnerability_data, session)

            # Step 2: build the scenario prompt. First turn uses the default
            # template; later turns build an adaptive one from the feedback.
            if turn_num == 0 or previous_template is None:
                scenario_attack = self._default_template(rewritten_content)
            else:
                scenario_attack = await self._adaptive_template(
                    rewritten_content,
                    previous_template,
                    previous_assistant_response or "",
                    vulnerability_data,
                    session,
                )

            # Step 3: optional turn-level technique, then send to the target.
            scenario_attack, turn_level_attack = await session.enhance_turn(scenario_attack)
            reply = await send_turn(
                session, turns, scenario_attack, turn_level_attack=turn_level_attack
            )
            assistant_response = reply.content

            # Step 4: a refusal from the target ends the attack.
            if await session.is_refusal(scenario_attack, assistant_response):
                return False

            # Step 5: judge the answer. Harmful means the jailbreak worked.
            if await self._judge(
                original_attack, scenario_attack, assistant_response, vulnerability_data, session
            ):
                return True

            # Step 6: escalate. Improve the base attack for the next turn;
            # keep the current one if the attacker cannot improve it.
            judge_feedback = "Classification: Not harmful"
            improvement_prompt = SequentialBreakTemplate.improve_attack_prompt(
                original_attack,
                scenario_attack,
                assistant_response,
                judge_feedback,
                self.attack_type,
                vulnerability_data,
            )
            try:
                improved: ImprovedAttack = await session.generate(
                    improvement_prompt, ImprovedAttack
                )
                base_attack = improved.improved_attack
            except GenerationError:
                pass

            previous_template = scenario_attack
            previous_assistant_response = assistant_response

        return False

    # ------------------------------------------------------------------
    # Per-type helpers
    # ------------------------------------------------------------------

    async def _rewrite(
        self, base_attack: str, vulnerability_data: str, session: AttackSession
    ) -> str:
        if self.attack_type == "question_bank":
            prompt = SequentialBreakTemplate.rewrite_question_bank_prompt(
                base_attack, vulnerability_data
            )
        elif self.attack_type == "game_environment":
            prompt = SequentialBreakTemplate.rewrite_game_environment_prompt(
                base_attack, vulnerability_data
            )
        else:
            prompt = SequentialBreakTemplate.rewrite_dialogue_prompt(
                base_attack, vulnerability_data
            )
        rewritten: RewrittenDialogue = await session.generate(prompt, RewrittenDialogue)
        content = rewritten.paraphrased_version
        content = content.replace("Paraphrased version:", "").strip()
        content = content.replace("<end>", "").strip()
        return content

    def _default_template(self, rewritten_content: str) -> str:
        if self.attack_type == "question_bank":
            return SequentialBreakTemplate.get_question_bank_template(rewritten_content)
        if self.attack_type == "game_environment":
            return SequentialBreakTemplate.get_game_environment_template(rewritten_content)
        return SequentialBreakTemplate.get_dialogue_template(rewritten_content, self.persona)

    async def _adaptive_template(
        self,
        rewritten_content: str,
        previous_template: str,
        previous_assistant_response: str,
        vulnerability_data: str,
        session: AttackSession,
    ) -> str:
        adaptive_judge_feedback = "Previous attempt was not successful"
        if previous_assistant_response:
            adaptive_judge_feedback += (
                f"\nPrevious response: {previous_assistant_response[:500]}"
            )

        if self.attack_type == "question_bank":
            prompt = SequentialBreakTemplate.generate_adaptive_question_bank_template(
                rewritten_content,
                previous_template,
                previous_assistant_response,
                adaptive_judge_feedback,
                vulnerability_data,
            )
            res: AdaptiveQuestionBankTemplate = await session.generate(
                prompt, AdaptiveQuestionBankTemplate
            )
            return res.template
        if self.attack_type == "game_environment":
            prompt = SequentialBreakTemplate.generate_adaptive_game_environment_template(
                rewritten_content,
                previous_template,
                previous_assistant_response,
                adaptive_judge_feedback,
                vulnerability_data,
            )
            res_g: AdaptiveGameEnvironmentTemplate = await session.generate(
                prompt, AdaptiveGameEnvironmentTemplate
            )
            return res_g.template
        prompt = SequentialBreakTemplate.generate_adaptive_dialogue_template(
            rewritten_content,
            self.persona or "student",
            previous_template,
            previous_assistant_response,
            adaptive_judge_feedback,
            vulnerability_data,
        )
        res_d: AdaptiveDialogueTemplate = await session.generate(
            prompt, AdaptiveDialogueTemplate
        )
        return res_d.template

    async def _judge(
        self,
        original_attack: str,
        scenario_attack: str,
        assistant_response: str,
        vulnerability_data: str,
        session: AttackSession,
    ) -> bool:
        if self.attack_type == "question_bank":
            prompt = SequentialBreakTemplate.question_bank_judge(
                original_attack, scenario_attack, assistant_response, vulnerability_data
            )
            judge_qb: QuestionBankJudge = await session.generate(prompt, QuestionBankJudge)
            return judge_qb.classification == "Harmful"
        if self.attack_type == "game_environment":
            prompt = SequentialBreakTemplate.game_environment_judge(
                original_attack, scenario_attack, assistant_response, vulnerability_data
            )
            judge_ge: GameEnvironmentJudge = await session.generate(
                prompt, GameEnvironmentJudge
            )
            return judge_ge.classification == "Harmful"
        prompt = SequentialBreakTemplate.dialogue_judge(
            original_attack, scenario_attack, assistant_response, vulnerability_data
        )
        judge_d: DialogueJudge = await session.generate(prompt, DialogueJudge)
        return judge_d.classification == "Harmful"
