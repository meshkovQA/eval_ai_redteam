"""Core data shapes shared by every layer of the kernel.

Written fresh for eval_ai_redteam. The field names deliberately mirror
deepteam's ``RTTestCase`` / ``RTTurn`` (input, actual_output, turns,
score, reason, attack_method) so platform code written against the old
runtime maps one-to-one, but the objects are plain pydantic models with
no deepeval base class and with an explicit ``status`` instead of a
free-form ``error`` string.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    """Where a test case ended up. ``OK`` means it was judged."""

    OK = "ok"
    # The attacker LLM could not produce a baseline attack for the seed.
    SIMULATION_ERROR = "simulation_error"
    # The attacker LLM refused to craft the attack (single-turn technique
    # or multi-turn turn generation). The baseline input is kept so the
    # caller can decide to send it unenhanced, but it was NOT sent.
    ATTACKER_REFUSED = "attacker_refused"
    # The technique could not be applied (parse failures, validity checks
    # never passed). Unlike deepteam we do not silently fall back to the
    # baseline: the row says so and ``technique_applied`` is False.
    TECHNIQUE_FAILED = "technique_failed"
    # The system under test raised / returned an error.
    TARGET_ERROR = "target_error"
    # The judge LLM failed to return a verdict.
    JUDGE_ERROR = "judge_error"
    # A multi-turn attack ran out of its call / time budget before
    # reaching a verdict. Turns collected so far are kept and judged.
    BUDGET_EXHAUSTED = "budget_exhausted"


class RTTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    retrieval_context: Optional[list[str]] = None
    tools_called: Optional[list[Any]] = None
    # Name of the single-turn technique applied to this specific user
    # turn inside a multi-turn attack (deepteam calls it the same).
    turn_level_attack: Optional[str] = None


class RTTestCase(BaseModel):
    """One (vulnerability, type, attack) attempt against the target."""

    vulnerability: str
    vulnerability_type: str
    risk_category: Optional[str] = None
    attack_method: Optional[str] = None
    # True only when the technique's output was actually sent. False for
    # baseline sends, refused enhancements and deterministic no-ops.
    technique_applied: bool = False

    # The seed produced by the vulnerability template (before technique).
    baseline_input: Optional[str] = None
    # What was actually sent to the target (single-turn).
    input: Optional[str] = None
    actual_output: Optional[str] = None
    retrieval_context: Optional[list[str]] = None
    tools_called: Optional[list[Any]] = None
    # Full transcript for multi-turn attacks (single-turn leaves it None).
    turns: Optional[list[RTTurn]] = None

    score: Optional[float] = None
    reason: Optional[str] = None
    status: CaseStatus = CaseStatus.OK
    error: Optional[str] = None

    # Cost accounting, filled by the engine.
    attacker_calls: int = 0
    target_calls: int = 0
    judge_calls: int = 0

    metadata: Optional[dict[str, Any]] = None

    @property
    def passed(self) -> Optional[bool]:
        """Platform-wide convention: score 1 = target stayed safe."""
        if self.status != CaseStatus.OK or self.score is None:
            return None
        return self.score > 0

    @property
    def last_assistant_content(self) -> Optional[str]:
        if self.turns:
            for turn in reversed(self.turns):
                if turn.role == "assistant" and turn.content:
                    return turn.content
        return self.actual_output


@dataclass(slots=True)
class Budget:
    """Hard caps for one multi-turn attack (per test case).

    Every multi-turn algorithm is a loop of attacker calls and target
    calls; TAP branches. Without caps a single row can eat hundreds of
    calls. Defaults are generous enough for the deepteam defaults
    (Crescendo 10 rounds x 3 attacker calls) and still bounded.
    """

    max_attacker_calls: int = 60
    max_target_calls: int = 30
    max_seconds: float = 600.0

    def start(self) -> "BudgetTracker":
        return BudgetTracker(self)


class BudgetExhausted(RuntimeError):
    pass


@dataclass(slots=True)
class BudgetTracker:
    budget: Budget
    attacker_calls: int = 0
    target_calls: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def charge_attacker(self) -> None:
        self.attacker_calls += 1
        if self.attacker_calls > self.budget.max_attacker_calls:
            raise BudgetExhausted(
                f"attacker call budget exhausted ({self.budget.max_attacker_calls})"
            )
        self._check_time()

    def charge_target(self) -> None:
        self.target_calls += 1
        if self.target_calls > self.budget.max_target_calls:
            raise BudgetExhausted(
                f"target call budget exhausted ({self.budget.max_target_calls})"
            )
        self._check_time()

    def _check_time(self) -> None:
        if time.monotonic() - self.started_at > self.budget.max_seconds:
            raise BudgetExhausted(
                f"time budget exhausted ({self.budget.max_seconds}s)"
            )

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at


# ============================================================
# Aggregation
# ============================================================


class VulnerabilityTypeResult(BaseModel):
    vulnerability: str
    vulnerability_type: str
    pass_rate: float
    passing: int
    failing: int
    errored: int


class AttackMethodResult(BaseModel):
    attack_method: str
    pass_rate: float
    passing: int
    failing: int
    errored: int


class RedTeamingOverview(BaseModel):
    vulnerability_type_results: list[VulnerabilityTypeResult]
    attack_method_results: list[AttackMethodResult]
    total: int
    passing: int
    failing: int
    errored: int
    pass_rate: float
    run_duration: float


class RiskAssessment(BaseModel):
    overview: RedTeamingOverview
    test_cases: list[RTTestCase]
    # Filled for framework runs: overview per risk category.
    categories: Optional[dict[str, RedTeamingOverview]] = None


def _stats(cases: list[RTTestCase]) -> tuple[int, int, int, float]:
    passing = sum(1 for c in cases if c.passed is True)
    errored = sum(1 for c in cases if c.status != CaseStatus.OK)
    failing = len(cases) - passing - errored
    valid = len(cases) - errored
    pass_rate = (passing / valid) if valid > 0 else 0.0
    return passing, failing, errored, pass_rate


def build_overview(
    test_cases: list[RTTestCase], run_duration: float = 0.0
) -> RedTeamingOverview:
    """Group cases by vulnerability type and by attack method."""
    by_type: dict[tuple[str, str], list[RTTestCase]] = {}
    by_attack: dict[str, list[RTTestCase]] = {}
    for case in test_cases:
        by_type.setdefault((case.vulnerability, case.vulnerability_type), []).append(case)
        if case.attack_method:
            by_attack.setdefault(case.attack_method, []).append(case)

    type_results = []
    for (vuln, vtype), cases in by_type.items():
        passing, failing, errored, rate = _stats(cases)
        type_results.append(
            VulnerabilityTypeResult(
                vulnerability=vuln,
                vulnerability_type=vtype,
                pass_rate=rate,
                passing=passing,
                failing=failing,
                errored=errored,
            )
        )
    attack_results = []
    for method, cases in by_attack.items():
        passing, failing, errored, rate = _stats(cases)
        attack_results.append(
            AttackMethodResult(
                attack_method=method,
                pass_rate=rate,
                passing=passing,
                failing=failing,
                errored=errored,
            )
        )
    passing, failing, errored, rate = _stats(test_cases)
    return RedTeamingOverview(
        vulnerability_type_results=type_results,
        attack_method_results=attack_results,
        total=len(test_cases),
        passing=passing,
        failing=failing,
        errored=errored,
        pass_rate=rate,
        run_duration=run_duration,
    )


def build_risk_assessment(
    test_cases: list[RTTestCase], run_duration: float = 0.0
) -> RiskAssessment:
    return RiskAssessment(
        overview=build_overview(test_cases, run_duration), test_cases=test_cases
    )
