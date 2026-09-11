"""Judge layer: one LLM call per test case, ``{"score", "reason"}`` back.

The prompt itself comes from the vulnerability (``judge_template``); this
package holds the shared response schema, transcript formatting and the
call wrapper that turns a ``GenerationError`` into a typed result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..llm import BaseLLM, GenerationError
from .format import format_actual_output, format_tools_called, format_turns
from .schema import Entities, Purpose, ReasonScore


@dataclass(slots=True)
class Verdict:
    score: Optional[float]
    reason: Optional[str]
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.score is not None


async def run_judge(judge_llm: BaseLLM, prompt: str, *, temperature: float = 0.0) -> Verdict:
    """Ask the judge; never raises. Score is clamped to [0, 1]."""
    try:
        res = await judge_llm.generate(prompt, ReasonScore, temperature=temperature)
    except GenerationError as exc:
        return Verdict(score=None, reason=None, error=f"judge returned no verdict: {exc}")
    except Exception as exc:  # transport failure
        return Verdict(score=None, reason=None, error=f"judge call failed: {exc}")
    score = max(0.0, min(1.0, float(res.score)))
    return Verdict(score=score, reason=res.reason)


__all__ = [
    "Verdict",
    "run_judge",
    "ReasonScore",
    "Purpose",
    "Entities",
    "format_turns",
    "format_tools_called",
    "format_actual_output",
]
