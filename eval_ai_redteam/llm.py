"""LLM transport layer for the attacker and the judge.

Written fresh for eval_ai_redteam (the structured-output helpers were
first written for the TestAgent platform's deepteam bridge and moved
here). The kernel needs exactly one primitive from a model: "complete
these chat messages, optionally in JSON matching this schema". Everything
else (retries, prompt steering, lenient JSON extraction, refusal
detection) lives here so attack and judge code stays declarative.

Implement ``BaseLLM.complete`` for your transport, or use:

  * ``CallableLLM`` to wrap any ``async (messages, temperature,
    response_format) -> str`` coroutine (platform gateways, tests).
  * ``EvalLibLLM`` to route through eval-ai-library (LiteLLM, 100+
    providers, per-call api_key / api_base).
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

Messages = list[dict[str, str]]


class GenerationError(RuntimeError):
    """The model did not return something parseable into ``schema``.

    ``raw_text`` carries the last raw response so callers can classify
    the failure (a prose refusal is the common case).
    """

    def __init__(self, message: str, *, raw_text: str = "") -> None:
        super().__init__(message)
        self.raw_text = raw_text


class BaseLLM(ABC):
    """One chat-completion primitive plus a structured ``generate``.

    Subclasses implement ``complete``. ``generate`` adds:
      1. native structured output via ``response_format`` (OpenAI
         json_schema shape, which LiteLLM forwards to every provider that
         supports it);
      2. a prompt-steered fallback when the provider rejects the
         response_format or returns unparseable text;
      3. lenient JSON extraction (fenced blocks, preambles, several
         objects in one reply);
      4. bounded retries.
    """

    max_retries: int = 3
    # Set False for transports that 4xx on response_format; generate()
    # then goes straight to the prompt-steered path.
    supports_structured_output: bool = True

    @abstractmethod
    async def complete(
        self,
        messages: Messages,
        *,
        temperature: float = 0.0,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        """Return the assistant text for ``messages``."""

    def get_model_name(self) -> str:
        return self.__class__.__name__

    async def generate(
        self,
        prompt: Optional[str] = None,
        schema: Optional[type[T]] = None,
        *,
        messages: Optional[Messages] = None,
        system: Optional[str] = None,
        temperature: float = 0.0,
    ) -> Union[str, T]:
        """Plain text when ``schema`` is None, else a validated instance.

        Pass either ``prompt`` (wrapped as one user message, with an
        optional ``system``) or a full ``messages`` list (multi-turn
        attacker chats such as Crescendo keep their own history).
        """
        msgs = _build_messages(prompt, messages, system)
        if schema is None:
            return await self.complete(msgs, temperature=temperature)

        last_error: Optional[BaseException] = None
        last_text = ""
        modes = self._mode_sequence()
        for attempt in range(self.max_retries):
            # Modes the endpoint rejects are dropped as we learn about
            # them, so a rejected json_schema is followed by json_object
            # in the same call, not by a wasted plain attempt.
            mode = modes.pop(0) if modes else "plain"
            try:
                if mode == "json_schema":
                    text = await self.complete(
                        msgs,
                        temperature=temperature,
                        response_format=to_response_format(schema),
                    )
                elif mode == "json_object":
                    text = await self.complete(
                        augment_messages_with_schema(msgs, schema),
                        temperature=temperature,
                        response_format={"type": "json_object"},
                    )
                else:
                    text = await self.complete(
                        augment_messages_with_schema(msgs, schema),
                        temperature=temperature,
                    )
            except Exception as exc:  # provider error, refused response_format, network
                last_error = exc
                self._note_provider_error(mode, exc)
                logger.debug("generate attempt %d (%s) failed: %s", attempt + 1, mode, exc)
                continue
            last_text = text if isinstance(text, str) else str(text)
            parsed = try_parse_schema(last_text, schema)
            if parsed is not None:
                return parsed
            last_error = GenerationError(
                f"could not parse {schema.__name__} from model output "
                f"(mode={mode}): {_preview(last_text)}",
                raw_text=last_text,
            )
            # A refusal will not become JSON on retry; stop early so the
            # caller can classify it instead of burning the retry budget.
            if looks_like_refusal(last_text):
                break
        raise GenerationError(
            f"{self.get_model_name()}: failed to produce {schema.__name__} "
            f"after {self.max_retries} attempt(s): {last_error}",
            raw_text=last_text,
        ) from last_error


    # ----- structured-output capability memory ---------------------------
    #
    # Providers differ: OpenAI's older chat models (gpt-3.5-turbo) reject
    # ``json_schema`` with a 400 but accept ``json_object``; some proxies
    # reject both. Each instance remembers what its endpoint refused so
    # later calls skip the doomed attempt instead of paying for it every
    # time. Attempt order is json_schema, then json_object with a steered
    # prompt, then a plain steered prompt; modes the endpoint refused are
    # dropped and the remaining budget is spent on the plain path.

    _json_schema_unsupported: bool = False
    _json_object_unsupported: bool = False

    def _mode_sequence(self) -> list[str]:
        modes: list[str] = []
        if self.supports_structured_output and not self._json_schema_unsupported:
            modes.append("json_schema")
        if not self._json_object_unsupported:
            modes.append("json_object")
        modes.append("plain")
        return modes

    def _note_provider_error(self, mode: str, exc: BaseException) -> None:
        text = str(exc).lower()
        if "response_format" not in text and "json" not in text and "structured" not in text:
            return  # transient / unrelated failure: keep trying the mode later
        if mode == "json_schema":
            self._json_schema_unsupported = True
            logger.info("%s does not accept json_schema output; falling back", self.get_model_name())
        elif mode == "json_object":
            self._json_object_unsupported = True
            logger.info("%s does not accept json_object output; falling back", self.get_model_name())


def _preview(text: str, limit: int = 160) -> str:
    flat = " ".join((text or "").split())
    return flat[:limit] + ("..." if len(flat) > limit else "")


class CallableLLM(BaseLLM):
    """Wrap a coroutine ``fn(messages, temperature, response_format) -> str``."""

    def __init__(
        self,
        fn: Callable[[Messages, float, Optional[dict[str, Any]]], Awaitable[str]],
        *,
        name: str = "callable-llm",
        supports_structured_output: bool = True,
        max_retries: int = 3,
    ) -> None:
        self._fn = fn
        self._name = name
        self.supports_structured_output = supports_structured_output
        self.max_retries = max_retries

    async def complete(
        self,
        messages: Messages,
        *,
        temperature: float = 0.0,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        return await self._fn(messages, temperature, response_format)

    def get_model_name(self) -> str:
        return self._name


class EvalLibLLM(BaseLLM):
    """Route through ``eval_lib.llm_client.chat_complete``.

    ``llm`` is anything eval-ai-library accepts ("gpt-4o-mini",
    "anthropic:claude-...", an ``LLMDescriptor`` or a ``CustomLLMClient``).
    Per-call credentials go through ``api_key`` / ``api_base`` /
    ``extra_kwargs`` exactly as in the library; ``response_format`` is
    forwarded inside ``extra_kwargs`` so LiteLLM passes it to the provider.
    Cost reported by the library is accumulated in ``total_cost``.
    """

    def __init__(
        self,
        llm: Any,
        *,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        extra_kwargs: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> None:
        self._llm = llm
        self._api_key = api_key
        self._api_base = api_base
        self._extra_kwargs = dict(extra_kwargs or {})
        self.max_retries = max_retries
        self.total_cost: float = 0.0

    async def complete(
        self,
        messages: Messages,
        *,
        temperature: float = 0.0,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        try:
            from eval_lib.llm_client import chat_complete  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(
                "EvalLibLLM needs eval-ai-library: pip install 'eval-ai-redteam[evallib]'"
            ) from exc
        extra = dict(self._extra_kwargs)
        if response_format is not None:
            extra["response_format"] = response_format
        text, cost = await chat_complete(
            self._llm,
            messages,
            temperature,
            api_key=self._api_key,
            api_base=self._api_base,
            extra_kwargs=extra or None,
        )
        if cost:
            self.total_cost += float(cost)
        return text

    def get_model_name(self) -> str:
        return str(self._llm)


# ============================================================
# Messages
# ============================================================


def _build_messages(
    prompt: Optional[str], messages: Optional[Messages], system: Optional[str]
) -> Messages:
    if messages is not None:
        return [dict(m) for m in messages]
    if prompt is None:
        raise ValueError("generate() needs either prompt or messages")
    out: Messages = []
    if system:
        out.append({"role": "system", "content": system})
    out.append({"role": "user", "content": prompt})
    return out


def augment_messages_with_schema(messages: Messages, schema: type[BaseModel]) -> Messages:
    """Append a JSON-mode instruction to the last user message."""
    out = [dict(m) for m in messages]
    for m in reversed(out):
        if m.get("role") == "user":
            m["content"] = augment_prompt_with_schema(m.get("content", ""), schema)
            return out
    out.append({"role": "user", "content": augment_prompt_with_schema("", schema)})
    return out


# ============================================================
# Native structured output
# ============================================================


def to_response_format(schema: Any) -> dict[str, Any]:
    """OpenAI-style ``response_format`` for a Pydantic class.

    Falls back to a permissive ``json_object`` request when ``schema`` is
    not a Pydantic model.
    """
    name = getattr(schema, "__name__", "Response") or "Response"
    schema_dict: Optional[dict[str, Any]] = None
    method = getattr(schema, "model_json_schema", None)
    if callable(method):
        try:
            schema_dict = method()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("model_json_schema failed: %s", exc)
    if not isinstance(schema_dict, dict):
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": sanitise_schema_for_strict_mode(schema_dict),
            "strict": True,
        },
    }


def sanitise_schema_for_strict_mode(schema: dict[str, Any]) -> dict[str, Any]:
    """OpenAI strict mode: every object needs additionalProperties=false
    and a ``required`` list naming every property. Patched in place."""
    if not isinstance(schema, dict):
        return schema
    nodes: list[Any] = [schema]
    seen: set[int] = set()
    while nodes:
        node = nodes.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if isinstance(node, dict):
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node.setdefault("additionalProperties", False)
                node["required"] = list(node["properties"].keys())
            for value in node.values():
                if isinstance(value, (dict, list)):
                    nodes.append(value)
        elif isinstance(node, list):
            for value in node:
                if isinstance(value, (dict, list)):
                    nodes.append(value)
    return schema


# ============================================================
# Prompt-steered fallback
# ============================================================


def augment_prompt_with_schema(prompt: str, schema: Any) -> str:
    lines = _schema_field_lines(schema)
    if lines:
        return (
            f"{prompt}\n\n"
            "Reply with a single JSON object. Do not wrap it in Markdown "
            "fences. The object must contain these fields:\n" + "\n".join(lines)
        )
    return f"{prompt}\n\nReply with a single valid JSON object only."


def _schema_field_lines(schema: Any) -> list[str]:
    fields = getattr(schema, "model_fields", None)
    if not isinstance(fields, dict):
        return []
    lines = []
    for name, info in fields.items():
        annotation = getattr(info, "annotation", None)
        label = (
            getattr(annotation, "__name__", None) or str(annotation)
            if annotation is not None
            else "any"
        )
        lines.append(f"  - {name}: {label}")
    return lines


# ============================================================
# Lenient JSON extraction
# ============================================================


def try_parse_schema(text: str, schema: type[T]) -> Optional[T]:
    """Validate the first JSON object in ``text`` against ``schema``.

    Candidates in order: raw text, first fenced block, every balanced
    ``{...}`` block. Returns None when nothing validates.
    """
    if not isinstance(text, str):
        return None
    validate = getattr(schema, "model_validate", None)
    if not callable(validate):
        return None
    for candidate in iter_json_candidates(text):
        payload = safe_json_loads(candidate)
        if payload is None:
            continue
        for shaped in _shape_candidates(payload, schema):
            try:
                return validate(shaped)
            except Exception as exc:
                logger.debug("schema validation failed: %s", exc)
                continue
    return None


def _shape_candidates(payload: Any, schema: Any):
    """Yield ``payload`` and the obvious re-shapings of it.

    Models asked for ``{"data": [...]}`` often answer with the bare list;
    when the schema has exactly one list-typed field, wrap the list under
    that field. Same for a dict whose only key holds the list under a
    different name.
    """
    yield payload
    fields = getattr(schema, "model_fields", None)
    if not isinstance(fields, dict) or len(fields) != 1:
        return
    (name, info), = fields.items()
    annotation = getattr(info, "annotation", None)
    origin = getattr(annotation, "__origin__", None)
    is_list = annotation is list or origin is list
    if not is_list:
        return
    if isinstance(payload, list):
        yield {name: payload}
    elif isinstance(payload, dict) and len(payload) == 1:
        (value,) = payload.values()
        if isinstance(value, list) and name not in payload:
            yield {name: value}


def iter_json_candidates(text: str):
    stripped = text.strip()
    if stripped:
        yield stripped
    fenced = extract_fenced_json(stripped)
    if fenced and fenced != stripped:
        yield fenced
    yield from iter_balanced_braces(stripped)
    yield from iter_balanced_brackets(stripped)


def iter_balanced_brackets(text: str):
    """Yield each balanced top-level ``[...]`` block (bare JSON arrays)."""
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                yield text[start : i + 1]
                start = -1


_FENCE_RE = re.compile(r"```(?:json|jsonc)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)


def extract_fenced_json(text: str) -> Optional[str]:
    match = _FENCE_RE.search(text)
    if match is None:
        return None
    return match.group(1).strip() or None


def iter_balanced_braces(text: str):
    """Yield each balanced top-level ``{...}`` block, string-aware."""
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                yield text[start : i + 1]
                start = -1


def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


# ============================================================
# Refusal heuristic
# ============================================================

_REFUSAL_PATTERNS = re.compile(
    r"("
    r"\bI(?:'m| am) (?:sorry|unable|not able)\b"
    r"|\bI can(?:'t|not) (?:help|assist|provide|create|generate|comply|do that|write|fulfil)"
    r"|\bI won(?:'t|not)\b"
    r"|\bI will not\b"
    r"|\bI must (?:decline|refuse)\b"
    r"|\bcannot (?:assist|help|comply|fulfil|provide)\b"
    r"|\bnot (?:able|going) to (?:help|assist|provide|create)\b"
    r"|\bagainst (?:my|our) (?:guidelines|policies|policy)\b"
    r"|\bAs an AI(?: language model)?\b"
    r"|\bI do not (?:feel comfortable|generate|produce)\b"
    r"|\bне могу (?:помочь|выполнить|предоставить|создать)\b"
    r")",
    re.IGNORECASE,
)


def looks_like_refusal(text: Optional[str]) -> bool:
    """Cheap textual check for a safety refusal.

    Used to (a) stop retrying JSON parsing on prose refusals and (b) tag a
    test case ``ATTACKER_REFUSED`` instead of silently downgrading to the
    baseline attack. It is a heuristic: attacks and judges still run their
    own LLM-based compliance checks where deepteam did.
    """
    if not text:
        return False
    head = text.strip()[:400]
    return bool(_REFUSAL_PATTERNS.search(head))
