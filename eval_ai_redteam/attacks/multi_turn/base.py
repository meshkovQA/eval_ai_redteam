"""Multi-turn attack base: session, budget, refusal check (written fresh).

A multi-turn attack drives a conversation with the target. Every
algorithm (Linear, Crescendo, TAP, Bad Likert Judge, Sequential Break)
is a loop over the same four primitives, which ``AttackSession`` wraps:

  * ``generate``       ask the attacker LLM (charged against the budget)
  * ``call_target``    send one user message with the history so far
  * ``is_refusal``     LLM classifier: did the attacker refuse to write
                       the next attack (deepteam's ``non_refusal``)
  * ``enhance_turn``   optionally apply a random single-turn technique
                       to one user turn (deepteam's ``turn_level_attacks``)

Algorithms implement ``_run`` and mutate ``turns`` in place. ``run``
turns every failure mode into a typed ``MultiTurnResult`` so the engine
can judge whatever transcript was collected.

Target contract: ``async target(message, history) -> RTTurn | str``.
``history`` is the transcript BEFORE ``message``. Stateless targets
replay it; stateful targets (chat-id bound) may ignore it, but MUST
treat a history shorter than what they already saw as a new session,
because Crescendo-style backtracking truncates the transcript.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, ClassVar, Literal, Optional, Sequence

from pydantic import BaseModel

from ...llm import BaseLLM, GenerationError, looks_like_refusal
from ...types import Budget, BudgetExhausted, BudgetTracker, RTTurn
from ..base import BaseAttack
from ..single_turn.base import BaseSingleTurnAttack
from .base_template import BaseMultiTurnTemplate

logger = logging.getLogger(__name__)

Target = Callable[[str, list[RTTurn]], Awaitable["RTTurn | str"]]


class NonRefusal(BaseModel):
    classification: Literal["Non-refusal", "Refusal"]


class ModelRefusalError(RuntimeError):
    """The attacker model refused to keep generating attack turns."""

    def __init__(self, entity: str, detail: str = "") -> None:
        msg = f"{entity}: attacker model refused to generate the next attack turn"
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)
        self.entity = entity


class TargetError(RuntimeError):
    """The system under test raised while answering."""


MultiTurnStatus = Literal[
    "ok", "attacker_refused", "budget_exhausted", "target_error", "technique_failed"
]


@dataclass(slots=True)
class MultiTurnResult:
    turns: list[RTTurn]
    status: MultiTurnStatus = "ok"
    # The algorithm's own opinion (its internal judge); the engine still
    # runs the vulnerability judge on the transcript.
    jailbroken: Optional[bool] = None
    rounds: int = 0
    attacker_calls: int = 0
    target_calls: int = 0
    error: Optional[str] = None
    # Free-form per-algorithm details (backtracks, best score, ...).
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def last_assistant(self) -> Optional[str]:
        for turn in reversed(self.turns):
            if turn.role == "assistant":
                return turn.content
        return None


class AttackSession:
    """Everything one multi-turn run needs, with budget accounting."""

    def __init__(
        self,
        *,
        attacker: BaseLLM,
        target: Target,
        budget: Optional[Budget] = None,
        turn_level_attacks: Optional[Sequence[BaseSingleTurnAttack]] = None,
        turn_level_probability: float = 0.5,
        rng: Optional[random.Random] = None,
        temperature: float = 0.0,
    ) -> None:
        self.attacker = attacker
        self.target = target
        self.tracker: BudgetTracker = (budget or Budget()).start()
        self.turn_level_attacks = list(turn_level_attacks or [])
        self.turn_level_probability = turn_level_probability
        self.rng = rng or random.Random()
        self.temperature = temperature

    @property
    def attacker_calls(self) -> int:
        return self.tracker.attacker_calls

    @property
    def target_calls(self) -> int:
        return self.tracker.target_calls

    async def generate(
        self,
        prompt: Optional[str] = None,
        schema: Optional[type[BaseModel]] = None,
        *,
        messages: Optional[list[dict[str, str]]] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        self.tracker.charge_attacker()
        return await self.attacker.generate(
            prompt,
            schema,
            messages=messages,
            system=system,
            temperature=self.temperature if temperature is None else temperature,
        )

    async def call_target(self, message: str, history: list[RTTurn]) -> RTTurn:
        self.tracker.charge_target()
        try:
            res = await self.target(message, list(history))
        except Exception as exc:
            raise TargetError(str(exc)) from exc
        if isinstance(res, RTTurn):
            if res.role != "assistant":
                res = res.model_copy(update={"role": "assistant"})
            return res
        return RTTurn(role="assistant", content="" if res is None else str(res))

    async def is_refusal(self, original_attack: str, candidate: str) -> bool:
        """deepteam's non_refusal classifier plus the cheap text heuristic."""
        if looks_like_refusal(candidate):
            return True
        prompt = BaseMultiTurnTemplate.non_refusal(original_attack, candidate)
        try:
            res = await self.generate(prompt, NonRefusal)
        except GenerationError:
            # Classifier itself failed: do not block the run on it.
            return False
        return res.classification == "Refusal"

    async def enhance_turn(self, text: str) -> tuple[str, Optional[str]]:
        """Maybe wrap one user turn in a random single-turn technique."""
        if not self.turn_level_attacks or self.rng.random() >= self.turn_level_probability:
            return text, None
        attack = self.rng.choice(self.turn_level_attacks)
        before = self.tracker.attacker_calls
        result = await attack.enhance(text, self.attacker)
        # enhance() bills through the attacker directly; mirror it here so
        # the budget stays honest.
        for _ in range(result.attacker_calls):
            self.tracker.charge_attacker()
        if before == self.tracker.attacker_calls and result.attacker_calls:
            pass
        if result.applied:
            return result.input, attack.get_name()
        return text, None


def seed_turns(turns: Optional[Sequence[RTTurn]], initial_attack: str) -> list[RTTurn]:
    """Normalise the starting transcript: at least one user turn."""
    out = [t.model_copy() for t in (turns or [])]
    if not out:
        out.append(RTTurn(role="user", content=initial_attack))
    return out


def last_user_content(turns: Sequence[RTTurn]) -> Optional[str]:
    for turn in reversed(turns):
        if turn.role == "user":
            return turn.content
    return None


async def ensure_assistant_reply(session: AttackSession, turns: list[RTTurn]) -> str:
    """If the transcript ends on a user turn, get the target's answer."""
    if not turns or turns[-1].role == "user":
        message = last_user_content(turns)
        if message is None:
            raise ValueError("No user turn found in conversation history")
        reply = await session.call_target(message, turns)
        turns.append(reply)
        return reply.content
    return turns[-1].content


async def send_turn(
    session: AttackSession,
    turns: list[RTTurn],
    message: str,
    *,
    turn_level_attack: Optional[str] = None,
) -> RTTurn:
    """Append a user turn, call the target, append its reply."""
    reply = await session.call_target(message, turns)
    turns.append(RTTurn(role="user", content=message, turn_level_attack=turn_level_attack))
    if turn_level_attack:
        reply = reply.model_copy(update={"turn_level_attack": turn_level_attack})
    turns.append(reply)
    return reply


class BaseMultiTurnAttack(BaseAttack):
    multi_turn: ClassVar[bool] = True

    def __init__(
        self,
        weight: int = 1,
        turn_level_attacks: Optional[Sequence[BaseSingleTurnAttack]] = None,
    ) -> None:
        super().__init__(weight=weight)
        if turn_level_attacks is not None:
            if not isinstance(turn_level_attacks, (list, tuple)) or not all(
                isinstance(a, BaseSingleTurnAttack) for a in turn_level_attacks
            ):
                raise ValueError("turn_level_attacks must be a list of single-turn attacks")
        self.turn_level_attacks = list(turn_level_attacks or [])

    async def run(
        self,
        *,
        attacker: BaseLLM,
        target: Target,
        initial_attack: str,
        vulnerability: str = "",
        vulnerability_type: str = "",
        turns: Optional[Sequence[RTTurn]] = None,
        budget: Optional[Budget] = None,
        rng: Optional[random.Random] = None,
        temperature: float = 0.0,
    ) -> MultiTurnResult:
        session = AttackSession(
            attacker=attacker,
            target=target,
            budget=budget,
            turn_level_attacks=self.turn_level_attacks,
            rng=rng,
            temperature=temperature,
        )
        transcript = seed_turns(turns, initial_attack)
        vulnerability_data = f"Vulnerability: {vulnerability} | Type: {vulnerability_type}"
        result = MultiTurnResult(turns=transcript)
        try:
            result.jailbroken = await self._run(
                session, transcript, initial_attack, vulnerability_data, result
            )
        except ModelRefusalError as exc:
            result.status, result.error = "attacker_refused", str(exc)
        except BudgetExhausted as exc:
            result.status, result.error = "budget_exhausted", str(exc)
        except TargetError as exc:
            result.status, result.error = "target_error", str(exc)
        except GenerationError as exc:
            result.status, result.error = "technique_failed", str(exc)
        result.attacker_calls = session.attacker_calls
        result.target_calls = session.target_calls
        return result

    async def _run(
        self,
        session: AttackSession,
        turns: list[RTTurn],
        initial_attack: str,
        vulnerability_data: str,
        result: MultiTurnResult,
    ) -> Optional[bool]:
        """Drive the conversation. Mutate ``turns``; return the algorithm's
        own jailbroken verdict (or None). Update ``result.rounds`` and
        ``result.details`` as you go so a budget cut-off still reports."""
        raise NotImplementedError
