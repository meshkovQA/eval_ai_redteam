"""Shared fakes: an attacker/judge LLM with canned answers and simple targets."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

import pytest
from pydantic import BaseModel

from eval_ai_redteam.llm import BaseLLM
from eval_ai_redteam.types import RTTurn


class FakeLLM(BaseLLM):
    """Answers from a queue, or from a router callable.

    * ``responses``: consumed in order. Each item may be a str, a dict
      (json-dumped) or a pydantic model (dumped as JSON).
    * ``router(messages, response_format) -> item``: computed answers,
      handy for multi-turn loops where order is hard to script.
    Every call is recorded in ``calls`` as (messages, response_format).
    """

    def __init__(
        self,
        responses: Optional[list[Any]] = None,
        *,
        router: Optional[Callable[[list[dict[str, str]], Optional[dict]], Any]] = None,
        name: str = "fake-llm",
        supports_structured_output: bool = True,
        max_retries: int = 3,
    ) -> None:
        self._queue = list(responses or [])
        self._router = router
        self._name = name
        self.supports_structured_output = supports_structured_output
        self.max_retries = max_retries
        self.calls: list[tuple[list[dict[str, str]], Optional[dict]]] = []

    async def complete(self, messages, *, temperature=0.0, response_format=None):
        self.calls.append(([dict(m) for m in messages], response_format))
        if self._router is not None:
            item = self._router(messages, response_format)
        else:
            if not self._queue:
                raise AssertionError(
                    f"FakeLLM {self._name} ran out of responses after {len(self.calls)} calls; "
                    f"last prompt: {messages[-1]['content'][:200]!r}"
                )
            item = self._queue.pop(0)
        return _to_text(item)

    def get_model_name(self) -> str:
        return self._name

    @property
    def prompts(self) -> list[str]:
        return [m[-1]["content"] for m, _ in self.calls]


def _to_text(item: Any) -> str:
    if isinstance(item, BaseModel):
        return item.model_dump_json()
    if isinstance(item, (dict, list)):
        return json.dumps(item)
    if isinstance(item, Exception):
        raise item
    return str(item)


class EchoTarget:
    """Replies with a fixed or computed answer; records every call."""

    def __init__(self, reply: str | Callable[[str, list[RTTurn]], str] = "Sure, here you go."):
        self.reply = reply
        self.calls: list[tuple[str, list[RTTurn]]] = []

    async def __call__(self, message: str, history: list[RTTurn]):
        self.calls.append((message, list(history)))
        if callable(self.reply):
            return self.reply(message, history)
        return self.reply


class FailingTarget:
    async def __call__(self, message: str, history: list[RTTurn]):
        raise RuntimeError("connector down")


@pytest.fixture
def echo_target() -> EchoTarget:
    return EchoTarget()


@pytest.fixture
def refusing_target() -> EchoTarget:
    return EchoTarget("I'm sorry, I can't help with that.")


@pytest.fixture
def failing_target() -> FailingTarget:
    return FailingTarget()


def reason_score(score: float, reason: str = "because") -> dict:
    return {"score": score, "reason": reason}


def synthetic(*inputs: str) -> dict:
    return {"data": [{"input": i} for i in inputs]}
