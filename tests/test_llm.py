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
    # No json_schema: the first attempt is json_object mode with a
    # steered prompt (providers require the word JSON in the prompt).
    llm = FakeLLM([{"score": 0, "reason": "x"}], supports_structured_output=False)
    await llm.generate("judge", Verdict)
    messages, rf = llm.calls[0]
    assert rf == {"type": "json_object"}
    assert "Reply with a single JSON object" in messages[-1]["content"]


async def test_generate_retries_on_garbage_then_succeeds():
    llm = FakeLLM(["nonsense", {"score": 1, "reason": "second try"}])
    res = await llm.generate("judge", Verdict)
    assert res.reason == "second try"
    assert len(llm.calls) == 2
    # the retry goes through json_object mode with the steered prompt
    assert llm.calls[1][1] == {"type": "json_object"}
    assert "Reply with a single JSON object" in llm.calls[1][0][-1]["content"]


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


# ---------------------------------------------------------------- structured-output fallbacks


class ItemList(BaseModel):
    data: list[Verdict]


def test_bare_array_is_wrapped_into_single_list_field():
    text = '[{"score": 1, "reason": "a"}, {"score": 0, "reason": "b"}]'
    res = try_parse_schema(text, ItemList)
    assert res is not None and [v.reason for v in res.data] == ["a", "b"]
    # a wrongly named single key holding the list is accepted too
    assert try_parse_schema('{"items": [{"score": 1, "reason": "a"}]}', ItemList).data[0].score == 1
    # but a multi-field schema is never reshaped
    assert try_parse_schema('[{"score": 1}]', Verdict) is None


async def test_json_schema_rejection_falls_back_to_json_object_and_is_remembered():
    calls = []

    async def fn(messages, temperature, response_format):
        calls.append(response_format)
        if response_format and response_format.get("type") == "json_schema":
            raise RuntimeError("Invalid parameter: 'response_format' of type 'json_schema' is not supported with this model")
        return '{"data": [{"score": 1, "reason": "ok"}]}'

    llm = CallableLLM(fn, name="gpt-3.5")
    res = await llm.generate("make one", ItemList)
    assert res.data[0].score == 1
    assert [c and c.get("type") for c in calls] == ["json_schema", "json_object"]
    # the json_object request carries the steered prompt (providers require the word JSON)
    await llm.generate("again", ItemList)
    assert [c and c.get("type") for c in calls[2:]] == ["json_object"]


async def test_json_object_rejection_falls_back_to_plain_and_is_remembered():
    calls = []

    async def fn(messages, temperature, response_format):
        calls.append(response_format)
        if response_format is not None:
            raise RuntimeError("response_format is not supported by this endpoint")
        return '[{"score": 0, "reason": "plain"}]'

    llm = CallableLLM(fn, name="proxy")
    res = await llm.generate("go", ItemList)
    assert res.data[0].reason == "plain"
    assert [c and c.get("type") for c in calls] == ["json_schema", "json_object", None]
    await llm.generate("go", ItemList)
    assert calls[3:] == [None]


async def test_unrelated_transport_error_does_not_downgrade_capabilities():
    calls = []

    async def fn(messages, temperature, response_format):
        calls.append(response_format)
        if len(calls) == 1:
            raise RuntimeError("connection reset by peer")
        return '{"data": [{"score": 1, "reason": "ok"}]}'

    llm = CallableLLM(fn, name="flaky")
    await llm.generate("go", ItemList)
    await llm.generate("go", ItemList)
    # second call starts with json_schema again
    assert calls[-1]["type"] == "json_schema"


async def test_generation_error_carries_a_preview_of_the_output():
    llm = FakeLLM(["no json here at all", "still nothing", "nope"], max_retries=3)
    with pytest.raises(GenerationError) as exc:
        await llm.generate("judge", Verdict)
    assert "mode=" in str(exc.value) and "nope" in str(exc.value)
