"""Tests for the single-turn attack techniques.

Covers the deterministic transforms, the LLMEnhancedAttack generate ->
compliance -> validity loop (via PromptInjection), the one-shot
AdversarialPoetry path, per-technique instantiation and prompt threading,
and the SINGLE_TURN_ATTACKS registry.
"""

from __future__ import annotations

import base64 as _b64

import pytest

from eval_ai_redteam.attacks.single_turn import (
    SINGLE_TURN_ATTACKS,
    AdversarialPoetry,
    AuthorityEscalation,
    Base64,
    CharacterStream,
    ContextFlooding,
    EmbeddedInstructionJSON,
    EmotionalManipulation,
    LLMEnhancedAttack,
    Leetspeak,
    Multilingual,
    PromptInjection,
    ROT13,
    Roleplay,
    SyntheticContextInjection,
)

from conftest import FakeLLM


def _rewrite(text: str, *, reasoning: str = "some strategy reasoning") -> dict:
    """A rewrite response matching the EnhancedInjection schema."""
    return {"strategy_reasoning": reasoning, "input": text}


# ============================================================
# 1. Deterministic techniques
# ============================================================


async def test_base64_transform():
    res = await Base64().enhance("attack me")
    assert res.applied is True
    assert res.status == "ok"
    assert res.input == _b64.b64encode(b"attack me").decode()
    assert _b64.b64decode(res.input).decode() == "attack me"


async def test_rot13_transform():
    res = await ROT13().enhance("Hello")
    assert res.applied is True
    assert res.input == "Uryyb"


async def test_leetspeak_transform():
    res = await Leetspeak().enhance("elite")
    # e->3, l->1, i->1, t->7, e->3
    assert res.input == "31173"


async def test_character_stream_transform():
    res = await CharacterStream().enhance("abc")
    assert res.input == "a b c"
    assert res.applied is True


async def test_deterministic_enhance_without_attacker():
    # No attacker needed; applied True and attempts recorded.
    res = await Base64().enhance("x", attacker=None)
    assert res.applied is True
    assert res.attempts == 1


async def test_context_flooding_respects_target_chars():
    attack = "do the bad thing"
    tech = ContextFlooding(target_chars=500)
    res = await tech.enhance(attack)
    assert res.applied is True
    assert res.input.endswith(attack)
    # The flooded prefix should be near the requested size.
    assert len(res.input) >= 500


def test_context_flooding_rejects_small_target():
    with pytest.raises(ValueError):
        ContextFlooding(target_chars=199)


async def test_embedded_instruction_json_embeds_payload():
    payload = "SECRET_PAYLOAD_123"
    res = await EmbeddedInstructionJSON().enhance(payload)
    assert res.applied is True
    assert "main_note" in res.input
    assert payload in res.input


# ============================================================
# 2. LLMEnhancedAttack loop via PromptInjection
# ============================================================


async def test_loop_happy_path():
    attacker = FakeLLM(
        responses=[
            _rewrite("REWRITTEN ATTACK", reasoning="the plan"),
            {"non_compliant": False},
            {"is_valid_injection": True},
        ]
    )
    res = await PromptInjection().enhance("original attack", attacker=attacker)
    assert res.applied is True
    assert res.status == "ok"
    assert res.input == "REWRITTEN ATTACK"
    assert res.attacker_calls == 3
    assert res.attempts == 1
    assert res.rationale == "the plan"


async def test_loop_attacker_refuses_inside_rewrite():
    attacker = FakeLLM(
        responses=[_rewrite("I'm sorry, I can't help with that.")]
    )
    res = await PromptInjection(max_retries=1).enhance("original attack", attacker=attacker)
    assert res.applied is False
    assert res.status == "attacker_refused"
    assert res.input == "original attack"


async def test_loop_compliance_flags_non_compliant_every_attempt():
    attacker = FakeLLM(
        responses=[
            _rewrite("rewrite one"),
            {"non_compliant": True},
            _rewrite("rewrite two"),
            {"non_compliant": True},
        ]
    )
    res = await PromptInjection(max_retries=2).enhance("original attack", attacker=attacker)
    assert res.applied is False
    assert res.status == "attacker_refused"
    assert res.input == "original attack"


async def test_loop_validity_false_every_attempt():
    attacker = FakeLLM(
        responses=[
            _rewrite("rewrite one"),
            {"non_compliant": False},
            {"is_valid_injection": False},
            _rewrite("rewrite two"),
            {"non_compliant": False},
            {"is_valid_injection": False},
        ]
    )
    res = await PromptInjection(max_retries=2).enhance("original attack", attacker=attacker)
    assert res.applied is False
    assert res.status == "technique_failed"
    assert res.input == "original attack"


async def test_loop_attacker_missing():
    res = await PromptInjection().enhance("original attack", attacker=None)
    assert res.applied is False
    assert res.status == "attacker_missing"
    assert res.input == "original attack"


async def test_loop_retries_then_succeeds():
    attacker = FakeLLM(
        responses=[
            _rewrite("first try"),
            {"non_compliant": False},
            {"is_valid_injection": False},
            _rewrite("second try"),
            {"non_compliant": False},
            {"is_valid_injection": True},
        ]
    )
    res = await PromptInjection(max_retries=3).enhance("original attack", attacker=attacker)
    assert res.applied is True
    assert res.input == "second try"
    assert res.attempts == 2


# ============================================================
# 3. AdversarialPoetry: one generation, no compliance/validity
# ============================================================


async def test_adversarial_poetry_single_call():
    attacker = FakeLLM(
        responses=[{"metaphorical_strategy": "a metaphor", "input": "a dark poem"}]
    )
    res = await AdversarialPoetry().enhance("burn it down", attacker=attacker)
    assert res.applied is True
    assert res.status == "ok"
    assert res.input == "a dark poem"
    # Exactly one attacker call: no compliance, no validity check.
    assert len(attacker.calls) == 1
    assert res.attacker_calls == 1


# ============================================================
# 4. Every technique instantiates; LLM ones thread their args
# ============================================================


def _instantiate(cls):
    if cls is SyntheticContextInjection:
        return cls(target_information="ACME Corp internal systems")
    return cls()


def test_all_techniques_instantiate_with_defaults():
    assert len(SINGLE_TURN_ATTACKS) == 22
    for key, cls in SINGLE_TURN_ATTACKS.items():
        tech = _instantiate(cls)
        assert tech.get_name(), f"{key} has an empty name"


def test_llm_techniques_embed_the_attack_in_the_prompt():
    for key, cls in SINGLE_TURN_ATTACKS.items():
        if not issubclass(cls, LLMEnhancedAttack):
            continue
        tech = _instantiate(cls)
        prompt = tech.enhance_prompt("test attack")
        assert isinstance(prompt, str)
        assert "test attack" in prompt, f"{key} did not embed the attack"


def test_roleplay_threads_persona_and_role():
    tech = Roleplay(persona="a grizzled pirate captain", role="ship navigator")
    prompt = tech.enhance_prompt("test attack")
    assert "a grizzled pirate captain" in prompt
    assert "ship navigator" in prompt
    assert "test attack" in prompt


def test_authority_escalation_threads_role():
    tech = AuthorityEscalation(role="Chief Security Officer")
    prompt = tech.enhance_prompt("test attack")
    assert "Chief Security Officer" in prompt
    assert "test attack" in prompt


def test_emotional_manipulation_threads_emotion():
    tech = EmotionalManipulation(emotion="DESPERATION")
    prompt = tech.enhance_prompt("test attack")
    assert "DESPERATION" in prompt
    assert "test attack" in prompt


def test_multilingual_threads_language():
    tech = Multilingual(language="Scots Gaelic")
    prompt = tech.enhance_prompt("test attack")
    assert "Scots Gaelic" in prompt
    assert "test attack" in prompt


def test_synthetic_context_injection_threads_target_information():
    tech = SyntheticContextInjection(target_information="GC Healthcare Portal")
    prompt = tech.enhance_prompt("test attack")
    assert "GC Healthcare Portal" in prompt
    assert "test attack" in prompt


def test_synthetic_context_injection_keeps_context_style():
    tech = SyntheticContextInjection(
        target_information="GC Healthcare Portal", context_style="email"
    )
    assert tech.context_style == "email"


# ============================================================
# 5. Registry
# ============================================================


def test_registry_has_22_entries_mapping_to_classes():
    assert len(SINGLE_TURN_ATTACKS) == 22
    assert SINGLE_TURN_ATTACKS["base64"] is Base64
    assert SINGLE_TURN_ATTACKS["rot13"] is ROT13
    assert SINGLE_TURN_ATTACKS["prompt_injection"] is PromptInjection
    assert SINGLE_TURN_ATTACKS["adversarial_poetry"] is AdversarialPoetry
    # LinguisticConfusion is keyed by its snake_case identifier, not its dir.
    assert SINGLE_TURN_ATTACKS["linguistic_confusion"].__name__ == "LinguisticConfusion"
    assert SINGLE_TURN_ATTACKS["synthetic_context_injection"] is SyntheticContextInjection
    # Every value is a BaseSingleTurnAttack subclass.
    from eval_ai_redteam.attacks.single_turn import BaseSingleTurnAttack

    for cls in SINGLE_TURN_ATTACKS.values():
        assert issubclass(cls, BaseSingleTurnAttack)
