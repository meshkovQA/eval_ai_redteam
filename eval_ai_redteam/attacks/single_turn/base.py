"""Single-turn technique base classes (written fresh).

Two flavours:

* ``DeterministicAttack``: a pure string transform (Base64, ROT13, ...).
  Never needs an attacker model, never fails.
* ``LLMEnhancedAttack``: the deepteam pattern "generate a rewrite, check
  the rewrite is not a refusal, check the rewrite really is the intended
  technique, retry up to N times". The difference from deepteam is the
  ending: when every attempt fails we return ``applied=False`` with an
  explicit status instead of silently handing back the baseline prompt
  under the technique's name.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, ClassVar, Optional

from pydantic import BaseModel

from ...llm import BaseLLM, GenerationError, looks_like_refusal
from ..base import BaseAttack

logger = logging.getLogger(__name__)


class ComplianceData(BaseModel):
    non_compliant: bool


@dataclass(slots=True)
class EnhanceResult:
    """Outcome of one ``enhance`` call.

    ``input`` is what to send: the enhanced prompt when ``applied`` is
    True, the untouched baseline otherwise. ``status`` is one of
    ``ok``, ``attacker_refused``, ``technique_failed``, ``attacker_missing``.
    """

    input: str
    applied: bool
    status: str = "ok"
    attempts: int = 0
    attacker_calls: int = 0
    error: Optional[str] = None
    # The attacker's private reasoning field (strategy_reasoning, ...),
    # useful for debugging why a rewrite looks the way it does.
    rationale: Optional[str] = None


class BaseSingleTurnAttack(BaseAttack):
    requires_llm: ClassVar[bool] = False

    async def enhance(self, attack: str, attacker: Optional[BaseLLM] = None) -> EnhanceResult:
        raise NotImplementedError


class DeterministicAttack(BaseSingleTurnAttack):
    def transform(self, attack: str) -> str:
        raise NotImplementedError

    async def enhance(self, attack: str, attacker: Optional[BaseLLM] = None) -> EnhanceResult:
        return EnhanceResult(input=self.transform(attack), applied=True, attempts=1)


class LLMEnhancedAttack(BaseSingleTurnAttack):
    """Generate / compliance-check / validity-check loop over a template.

    Subclasses bind:
      * ``template``          ported template class
      * ``enhanced_schema``   schema of the rewrite (must have ``input``)
      * ``validity_schema``   schema of the validity check, or None
      * ``validity_method``   template method producing the validity prompt
      * ``validity_field``    boolean field on ``validity_schema``
      * ``compliance_method`` template method for the refusal check
                              (None disables the check)
    and may override ``enhance_prompt`` when the template takes extra
    arguments (persona, role, language, ...).
    """

    requires_llm: ClassVar[bool] = True
    template: ClassVar[Any]
    enhanced_schema: ClassVar[type[BaseModel]]
    validity_schema: ClassVar[Optional[type[BaseModel]]] = None
    validity_method: ClassVar[Optional[str]] = None
    validity_field: ClassVar[Optional[str]] = None
    compliance_method: ClassVar[Optional[str]] = "non_compliant"
    input_field: ClassVar[str] = "input"

    def __init__(self, weight: int = 1, max_retries: int = 3) -> None:
        super().__init__(weight=weight)
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        self.max_retries = max_retries

    # ----- prompts (override when the template takes extra args) --------

    def enhance_prompt(self, attack: str) -> str:
        return self.template.enhance(attack)

    def compliance_prompt(self, res: BaseModel) -> str:
        return getattr(self.template, self.compliance_method)(res.model_dump())

    def validity_prompt(self, res: BaseModel) -> str:
        return getattr(self.template, self.validity_method)(res.model_dump())

    # ----- loop ---------------------------------------------------------

    async def enhance(self, attack: str, attacker: Optional[BaseLLM] = None) -> EnhanceResult:
        if attacker is None:
            return EnhanceResult(
                input=attack,
                applied=False,
                status="attacker_missing",
                error=f"{self.get_name()} needs an attacker LLM",
            )
        calls = 0
        refused = False
        last_error: Optional[str] = None
        rationale: Optional[str] = None
        for attempt in range(1, self.max_retries + 1):
            # 1. rewrite
            calls += 1
            try:
                res = await attacker.generate(self.enhance_prompt(attack), self.enhanced_schema)
            except GenerationError as exc:
                last_error = str(exc)
                if looks_like_refusal(exc.raw_text):
                    refused = True
                    break
                continue
            candidate = getattr(res, self.input_field, None)
            if not isinstance(candidate, str) or not candidate.strip():
                last_error = "attacker returned an empty rewrite"
                continue
            rationale = _first_text_field(res, exclude=self.input_field)
            if looks_like_refusal(candidate):
                refused = True
                last_error = "attacker refused inside the rewrite"
                continue
            # 2. compliance check (did the attacker refuse in disguise?)
            if self.compliance_method:
                calls += 1
                try:
                    comp = await attacker.generate(self.compliance_prompt(res), ComplianceData)
                except GenerationError as exc:
                    last_error = f"compliance check failed: {exc}"
                    continue
                if comp.non_compliant:
                    refused = True
                    last_error = "attacker output flagged non-compliant"
                    continue
            # 3. validity check (is it really this technique?)
            if self.validity_schema and self.validity_method and self.validity_field:
                calls += 1
                try:
                    val = await attacker.generate(self.validity_prompt(res), self.validity_schema)
                except GenerationError as exc:
                    last_error = f"validity check failed: {exc}"
                    continue
                if not bool(getattr(val, self.validity_field, False)):
                    last_error = f"rewrite did not pass the {self.validity_field} check"
                    continue
            return EnhanceResult(
                input=candidate.strip(),
                applied=True,
                status="ok",
                attempts=attempt,
                attacker_calls=calls,
                rationale=rationale,
            )
        return EnhanceResult(
            input=attack,
            applied=False,
            status="attacker_refused" if refused else "technique_failed",
            attempts=self.max_retries,
            attacker_calls=calls,
            error=last_error,
            rationale=rationale,
        )


def _first_text_field(res: BaseModel, *, exclude: str) -> Optional[str]:
    for name, value in res.model_dump().items():
        if name != exclude and isinstance(value, str) and value.strip():
            return value
    return None
