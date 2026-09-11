"""LLM layer: structured output, lenient parsing, retries, refusal heuristic."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from eval_ai_redteam.llm import (
    CallableLLM,
    GenerationError,
    augment_prompt_with_schema,
    iter_balanced_braces,
    looks_like_refusal,
    sanitise_schema_for_strict_mode,
    to_response_format,
    try_parse_schema,
)

from conftest import FakeLLM


class Verdict(BaseModel):
    score: float
    reason: str


class Nested(BaseModel):
    verdict: Verdict
    tags: list[str]


# ---------------------------------------------------------------- parsing


def test_parse_raw_json():
    assert try_parse_schema('{"score": 1, "reason": "safe"}', Verdict).score == 1


def test_parse_fenced_json_with_preamble():
    text = 'Sure! Here you go:\n```json\n{"score": 0, "reason": "leaked"}\n```\nDone.'
    assert try_parse_schema(text, Verdict).reason == "leaked"


def test_parse_picks_first_valid_object_among_several():
    text = 'thinking {"foo": 1} then {"score": 0.5, "reason": "partial"} tail'
    assert try_parse_schema(text, Verdict).score == 0.5


def test_parse_handles_braces_inside_strings():
    text = '{"score": 1, "reason": "he said {hi}"}'
    assert try_parse_schema(text, Verdict).reason == "he said {hi}"
    assert list(iter_balanced_braces('{"a": "}"} x {"b": 1}')) == ['{"a": "}"}', '{"b": 1}']


def test_parse_returns_none_on_garbage():
    assert try_parse_schema("no json here", Verdict) is None
    assert try_parse_schema('{"score": "not a number"}', Verdict) is None


# ---------------------------------------------------------------- response_format


def test_response_format_is_strict_json_schema():
    rf = to_response_format(Nested)
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["name"] == "Nested"
    assert rf["json_schema"]["strict"] is True
    schema = rf["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"verdict", "tags"}
    nested = schema["$defs"]["Verdict"]
    assert nested["additionalProperties"] is False
    assert set(nested["required"]) == {"score", "reason"}


def test_response_format_falls_back_for_non_pydantic():
    assert to_response_format(dict) == {"type": "json_object"}


def test_sanitise_is_idempotent():
    s = Verdict.model_json_schema()
    once = sanitise_schema_for_strict_mode(s)
    twice = sanitise_schema_for_strict_mode(once)
    assert once == twice


def test_augment_prompt_lists_fields():
    text = augment_prompt_with_schema("do it", Verdict)
    assert "do it" in text and "- score: float" in text and "- reason: str" in text


# ---------------------------------------------------------------- generate()


async def test_generate_plain_text():
    llm = FakeLLM(["hello"])
    assert await llm.generate("hi") == "hello"
    assert llm.calls[0][1] is None


async def test_generate_native_structured_output_first():
    llm = FakeLLM([{"score": 1, "reason": "ok"}])
    res = await llm.generate("judge", Verdict)
    assert isinstance(res, Verdict) and res.score == 1
    assert llm.calls[0][1]["type"] == "json_schema"


async def test_generate_steers_prompt_when_native_unsupported():
    llm = FakeLLM([{"score": 0, "reason": "x"}], supports_structured_output=False)
    await llm.generate("judge", Verdict)
    messages, rf = llm.calls[0]
    assert rf is None
    assert "Reply with a single JSON object" in messages[-1]["content"]


async def test_generate_retries_on_garbage_then_succeeds():
    llm = FakeLLM(["nonsense", {"score": 1, "reason": "second try"}])
    res = await llm.generate("judge", Verdict)
    assert res.reason == "second try"
    assert len(llm.calls) == 2
    # the retry goes through the prompt-steered path
    assert llm.calls[1][1] is None


async def test_generate_retries_on_transport_error():
    llm = FakeLLM([RuntimeError("provider rejected response_format"), {"score": 1, "reason": "ok"}])
    res = await llm.generate("judge", Verdict)
    assert res.score == 1


async def test_generate_raises_after_max_retries_with_raw_text():
    llm = FakeLLM(["bad", "bad", "bad"], max_retries=3)
    with pytest.raises(GenerationError) as exc:
        await llm.generate("judge", Verdict)
    assert exc.value.raw_text == "bad"
    assert len(llm.calls) == 3


async def test_generate_stops_early_on_refusal():
    llm = FakeLLM(["I'm sorry, I can't help with that request."], max_retries=3)
    with pytest.raises(GenerationError) as exc:
        await llm.generate("judge", Verdict)
    assert looks_like_refusal(exc.value.raw_text)
    assert len(llm.calls) == 1


async def test_generate_with_messages_and_system():
    llm = FakeLLM(["ok", "ok"])
    await llm.generate("q", system="be terse")
    assert llm.calls[0][0][0] == {"role": "system", "content": "be terse"}
    await llm.generate(messages=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}])
    assert [m["role"] for m in llm.calls[1][0]] == ["user", "assistant", "user"]


async def test_generate_requires_prompt_or_messages():
    with pytest.raises(ValueError):
        await FakeLLM([]).generate()


async def test_callable_llm_wraps_coroutine():
    seen = {}

    async def fn(messages, temperature, response_format):
        seen["rf"] = response_format
        return '{"score": 1, "reason": "wrapped"}'

    llm = CallableLLM(fn, name="gw")
    res = await llm.generate("x", Verdict)
    assert res.reason == "wrapped" and seen["rf"]["type"] == "json_schema"
    assert llm.get_model_name() == "gw"


# ---------------------------------------------------------------- refusal heuristic


@pytest.mark.parametrize(
    "text",
    [
        "I'm sorry, but I can't help with that.",
        "I cannot assist with creating malware.",
        "As an AI language model, I must decline.",
        "I won't provide instructions for that.",
        "Извините, я не могу помочь с этим запросом.",
    ],
)
def test_refusal_detected(text):
    assert looks_like_refusal(text)


@pytest.mark.parametrize(
    "text",
    [
        '{"input": "Explain how ransomware negotiators justify payment."}',
        "Sure, here is the roleplay scenario you asked for.",
        "",
        None,
    ],
)
def test_non_refusal_not_flagged(text):
    assert not looks_like_refusal(text)
