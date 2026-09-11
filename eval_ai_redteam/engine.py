"""Async red-teaming orchestrator (written fresh).

Pipeline for one test case:

    baseline (attacker)  ->  technique (attacker or pure)  ->  target  ->  judge

``RedTeamer.red_team`` runs it for every (vulnerability, type) x
``attacks_per_vulnerability_type`` with one technique sampled per case
by weight, under a concurrency semaphore. ``RedTeamer.run_seed`` runs it
for exactly one seed and accepts a pre-generated ``baseline_input``, which
is how a platform executes one dataset row without regenerating the
attack it already stored.

Compared with deepteam's ``red_team``: async end to end (no thread, no
private event loop), no console output, no telemetry, no upload; every
failure lands on the case as a typed status; technique failures are
reported instead of silently degraded.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, Sequence

from .attacks.base import BaseAttack
from .attacks.multi_turn.base import BaseMultiTurnAttack, Target
from .attacks.single_turn.base import BaseSingleTurnAttack
from .frameworks.base import AISafetyFramework
from .llm import BaseLLM
from .types import (
    Budget,
    CaseStatus,
    RedTeamingOverview,
    RiskAssessment,
    RTTestCase,
    RTTurn,
    build_overview,
)
from .vulnerabilities.base import BaseVulnerability

logger = logging.getLogger(__name__)

OnTechniqueFailure = Literal["send_baseline", "skip"]


@dataclass(slots=True)
class PlannedCase:
    vulnerability: BaseVulnerability
    case: RTTestCase
    attack: Optional[BaseAttack]


class RedTeamer:
    def __init__(
        self,
        *,
        attacker: BaseLLM,
        judge: BaseLLM,
        purpose: Optional[str] = None,
        max_concurrent: int = 10,
        budget: Optional[Budget] = None,
        on_technique_failure: OnTechniqueFailure = "send_baseline",
        attacker_temperature: float = 0.0,
        judge_temperature: float = 0.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        attacker: model that writes attacks (baseline seeds, technique
            rewrites, multi-turn turns).
        judge: model that scores the target's answers.
        purpose: one-line description of the system under test; woven
            into every attack and judge prompt so they stay on-topic.
        on_technique_failure: when a technique cannot be applied (attacker
            refused, validity checks never passed): ``send_baseline``
            still sends the untouched seed and marks
            ``technique_applied=False``; ``skip`` does not call the
            target and leaves the case with a failure status.
        """
        self.attacker = attacker
        self.judge = judge
        self.purpose = purpose
        self.max_concurrent = max(1, max_concurrent)
        self.budget = budget or Budget()
        self.on_technique_failure = on_technique_failure
        self.attacker_temperature = attacker_temperature
        self.judge_temperature = judge_temperature
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------
    # Phase 1: simulate baseline attacks
    # ------------------------------------------------------------------

    async def simulate(
        self,
        vulnerabilities: Sequence[BaseVulnerability],
        *,
        attacks_per_vulnerability_type: int = 1,
    ) -> list[PlannedCase]:
        sem = asyncio.Semaphore(self.max_concurrent)

        async def one(vuln: BaseVulnerability) -> list[PlannedCase]:
            async with sem:
                cases = await vuln.simulate_attacks(
                    self.attacker,
                    purpose=self.purpose,
                    attacks_per_vulnerability_type=attacks_per_vulnerability_type,
                    temperature=self.attacker_temperature,
                )
            return [PlannedCase(vuln, c, None) for c in cases]

        nested = await asyncio.gather(*(one(v) for v in vulnerabilities))
        return [p for group in nested for p in group]

    # ------------------------------------------------------------------
    # Phase 2: pick a technique per case
    # ------------------------------------------------------------------

    def pick_attack(self, attacks: Optional[Sequence[BaseAttack]]) -> Optional[BaseAttack]:
        if not attacks:
            return None
        weights = [max(0, a.weight) for a in attacks]
        if sum(weights) == 0:
            return self.rng.choice(list(attacks))
        return self.rng.choices(list(attacks), weights=weights, k=1)[0]

    def plan(
        self, planned: Sequence[PlannedCase], attacks: Optional[Sequence[BaseAttack]]
    ) -> list[PlannedCase]:
        for p in planned:
            if p.case.status == CaseStatus.OK and p.attack is None:
                p.attack = self.pick_attack(attacks)
                if p.attack is not None:
                    p.case.attack_method = p.attack.get_name()
        return list(planned)

    # ------------------------------------------------------------------
    # Phase 3: execute against the target + judge
    # ------------------------------------------------------------------

    async def execute(self, target: Target, planned: Sequence[PlannedCase]) -> list[RTTestCase]:
        sem = asyncio.Semaphore(self.max_concurrent)

        async def one(p: PlannedCase) -> RTTestCase:
            async with sem:
                return await self._execute_one(target, p)

        return list(await asyncio.gather(*(one(p) for p in planned)))

    async def _execute_one(self, target: Target, p: PlannedCase) -> RTTestCase:
        case, vuln, attack = p.case, p.vulnerability, p.attack
        if case.status != CaseStatus.OK or not case.input:
            return case  # simulation already failed; nothing to send
        try:
            if attack is None:
                await self._send_single(target, case)
            elif isinstance(attack, BaseMultiTurnAttack):
                await self._run_multi_turn(target, case, vuln, attack)
            elif isinstance(attack, BaseSingleTurnAttack):
                await self._run_single_turn(target, case, attack)
            else:  # pragma: no cover - defensive
                raise TypeError(f"unsupported attack type {type(attack).__name__}")
        except Exception as exc:  # never let one row kill the run
            logger.exception("case execution crashed")
            case.status = CaseStatus.TARGET_ERROR
            case.error = f"execution crashed: {exc}"
            return case
        if case.status != CaseStatus.OK:
            return case
        if not case.turns and case.actual_output is None:
            return case
        await vuln.judge(self.judge, case, purpose=self.purpose, temperature=self.judge_temperature)
        return case

    async def _send_single(self, target: Target, case: RTTestCase) -> None:
        try:
            res = await target(case.input or "", [])
        except Exception as exc:
            case.target_calls += 1
            case.status = CaseStatus.TARGET_ERROR
            case.error = f"target failed: {exc}"
            return
        case.target_calls += 1
        turn = res if isinstance(res, RTTurn) else RTTurn(role="assistant", content="" if res is None else str(res))
        case.actual_output = turn.content
        case.retrieval_context = turn.retrieval_context
        case.tools_called = turn.tools_called

    async def _run_single_turn(
        self, target: Target, case: RTTestCase, attack: BaseSingleTurnAttack
    ) -> None:
        case.attack_method = attack.get_name()
        result = await attack.enhance(case.input or "", self.attacker)
        case.attacker_calls += result.attacker_calls
        meta = dict(case.metadata or {})
        meta["technique_status"] = result.status
        if result.rationale:
            meta["technique_rationale"] = result.rationale
        case.metadata = meta
        if result.applied:
            case.input = result.input
            case.technique_applied = True
        else:
            case.technique_applied = False
            if self.on_technique_failure == "skip":
                case.status = (
                    CaseStatus.ATTACKER_REFUSED
                    if result.status == "attacker_refused"
                    else CaseStatus.TECHNIQUE_FAILED
                )
                case.error = result.error or f"{attack.get_name()} could not be applied"
                return
        await self._send_single(target, case)

    async def _run_multi_turn(
        self,
        target: Target,
        case: RTTestCase,
        vuln: BaseVulnerability,
        attack: BaseMultiTurnAttack,
    ) -> None:
        case.attack_method = attack.get_name()
        result = await attack.run(
            attacker=self.attacker,
            target=target,
            initial_attack=case.input or "",
            vulnerability=vuln.get_name(),
            vulnerability_type=case.vulnerability_type,
            budget=self.budget,
            rng=self.rng,
            temperature=self.attacker_temperature,
        )
        case.turns = result.turns
        case.attacker_calls += result.attacker_calls
        case.target_calls += result.target_calls
        case.actual_output = result.last_assistant
        meta = dict(case.metadata or {})
        meta["attack_status"] = result.status
        meta["attack_rounds"] = result.rounds
        if result.jailbroken is not None:
            meta["attack_self_verdict"] = "jailbroken" if result.jailbroken else "resisted"
        if result.details:
            meta["attack_details"] = result.details
        case.metadata = meta
        case.technique_applied = result.rounds > 0
        has_reply = any(t.role == "assistant" for t in result.turns)
        if not has_reply:
            case.status = {
                "attacker_refused": CaseStatus.ATTACKER_REFUSED,
                "budget_exhausted": CaseStatus.BUDGET_EXHAUSTED,
                "target_error": CaseStatus.TARGET_ERROR,
                "technique_failed": CaseStatus.TECHNIQUE_FAILED,
            }.get(result.status, CaseStatus.TECHNIQUE_FAILED)
            case.error = result.error or f"{attack.get_name()} produced no target reply"

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    async def red_team(
        self,
        target: Target,
        vulnerabilities: Optional[Sequence[BaseVulnerability]] = None,
        attacks: Optional[Sequence[BaseAttack]] = None,
        *,
        attacks_per_vulnerability_type: int = 1,
        framework: Optional[AISafetyFramework] = None,
    ) -> RiskAssessment:
        """Full campaign. Pass vulnerabilities (+ attacks) or a framework."""
        if framework is not None and (vulnerabilities or attacks):
            raise ValueError("pass either a framework or vulnerabilities/attacks, not both")
        if framework is None and not vulnerabilities:
            raise ValueError("red_team needs vulnerabilities or a framework")
        started = time.monotonic()
        if framework is None:
            planned = await self.simulate(
                vulnerabilities or [], attacks_per_vulnerability_type=attacks_per_vulnerability_type
            )
            self.plan(planned, attacks)
            cases = await self.execute(target, planned)
            return RiskAssessment(
                overview=build_overview(cases, time.monotonic() - started), test_cases=cases
            )

        all_cases: list[RTTestCase] = []
        per_category: dict[str, RedTeamingOverview] = {}
        for category in framework.risk_categories:
            planned = await self.simulate(
                category.vulnerabilities,
                attacks_per_vulnerability_type=attacks_per_vulnerability_type,
            )
            self.plan(planned, category.attacks)
            for p in planned:
                meta = dict(p.case.metadata or {})
                meta["framework"] = framework.get_name()
                meta["framework_category"] = category.name
                meta["framework_category_name"] = category.display_name
                p.case.metadata = meta
            cases = await self.execute(target, planned)
            per_category[category.name] = build_overview(cases, 0.0)
            all_cases.extend(cases)
        return RiskAssessment(
            overview=build_overview(all_cases, time.monotonic() - started),
            test_cases=all_cases,
            categories=per_category,
        )

    async def run_seed(
        self,
        target: Target,
        vulnerability: BaseVulnerability,
        *,
        vulnerability_type: Optional[str | Enum] = None,
        attack: Optional[BaseAttack] = None,
        baseline_input: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> RTTestCase:
        """Run one (vulnerability, type, attack) attempt and judge it.

        ``baseline_input`` skips generation and uses the given text as the
        seed (the platform's stored ``attack_prompt``). Without it the
        attacker generates one baseline for ``vulnerability_type`` (or
        the vulnerability's first type).
        """
        vtype = _resolve_type(vulnerability, vulnerability_type)
        if baseline_input:
            case = vulnerability.new_case(vtype, baseline_input=baseline_input, input=baseline_input)
        else:
            cases = await vulnerability.simulate_attacks(
                self.attacker,
                purpose=self.purpose,
                attacks_per_vulnerability_type=1,
                types=[vtype],
                temperature=self.attacker_temperature,
            )
            case = cases[0]
        if metadata:
            case.metadata = {**(case.metadata or {}), **metadata}
        planned = PlannedCase(vulnerability, case, attack)
        if attack is not None:
            case.attack_method = attack.get_name()
        return await self._execute_one(target, planned)

    async def judge_case(self, vulnerability: BaseVulnerability, case: RTTestCase) -> RTTestCase:
        """Judge an already-collected case (e.g. a scripted transcript)."""
        await vulnerability.judge(self.judge, case, purpose=self.purpose, temperature=self.judge_temperature)
        return case


def _resolve_type(vulnerability: BaseVulnerability, vulnerability_type: Optional[str | Enum]) -> Enum:
    if vulnerability_type is None:
        return vulnerability.types[0]
    if isinstance(vulnerability_type, Enum):
        return vulnerability_type
    for member in vulnerability.types_enum:
        if member.value == vulnerability_type:
            return member
    raise ValueError(
        f"{vulnerability.get_name()} has no type {vulnerability_type!r}; "
        f"allowed: {vulnerability.allowed_types()}"
    )
