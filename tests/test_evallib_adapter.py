"""EvalLibLLM routes through eval_lib.llm_client.chat_complete (faked here)."""

from __future__ import annotations

import sys
import types

import pytest

from eval_ai_redteam.llm import EvalLibLLM


@pytest.fixture
def fake_eval_lib(monkeypatch):
    calls = []

    async def chat_complete(llm, messages, temperature=0.0, *, api_key=None, api_base=None, extra_kwargs=None):
        calls.append({"llm": llm, "messages": messages, "temperature": temperature, "api_key": api_key, "api_base": api_base, "extra_kwargs": extra_kwargs})
        return '{"score": 1, "reason": "via eval_lib"}', 0.0021

    pkg = types.ModuleType("eval_lib")
    mod = types.ModuleType("eval_lib.llm_client")
    mod.chat_complete = chat_complete
    pkg.llm_client = mod
    monkeypatch.setitem(sys.modules, "eval_lib", pkg)
    monkeypatch.setitem(sys.modules, "eval_lib.llm_client", mod)
    return calls


async def test_evallib_adapter_forwards_credentials_and_response_format(fake_eval_lib):
    from pydantic import BaseModel

    class Verdict(BaseModel):
        score: float
        reason: str

    llm = EvalLibLLM("openai:gpt-4o-mini", api_key="sk-test", api_base="https://proxy", extra_kwargs={"timeout": 30})
    res = await llm.generate("judge this", Verdict, temperature=0.3)
    assert res.reason == "via eval_lib"
    call = fake_eval_lib[0]
    assert call["llm"] == "openai:gpt-4o-mini" and call["api_key"] == "sk-test" and call["api_base"] == "https://proxy"
    assert call["temperature"] == 0.3
    assert call["extra_kwargs"]["timeout"] == 30
    assert call["extra_kwargs"]["response_format"]["type"] == "json_schema"
    assert llm.total_cost == pytest.approx(0.0021)
    assert llm.get_model_name() == "openai:gpt-4o-mini"


async def test_evallib_adapter_plain_text_has_no_response_format(fake_eval_lib):
    llm = EvalLibLLM("gpt-4o-mini")
    text = await llm.generate("hi")
    assert "via eval_lib" in text
    assert fake_eval_lib[0]["extra_kwargs"] is None


async def test_evallib_adapter_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "eval_lib", None)
    monkeypatch.setitem(sys.modules, "eval_lib.llm_client", None)
    with pytest.raises(ImportError, match="eval-ai-redteam\\[evallib\\]"):
        await EvalLibLLM("gpt-4o-mini").complete([{"role": "user", "content": "x"}])
