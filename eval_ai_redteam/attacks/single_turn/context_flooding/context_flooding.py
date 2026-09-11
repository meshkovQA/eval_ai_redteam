# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: rebased on DeterministicAttack.
from typing import Literal, Optional

from ...base import Exploitability
from ..base import DeterministicAttack
from .template import DEFAULT_PREFIXES

ContextFloodingPrefixType = Literal["enterprise", "logs", "transcript"]


class ContextFlooding(DeterministicAttack):
    name = "ContextFlooding"
    exploitability = Exploitability.MEDIUM
    description = "A single-turn attack that floods the LLM's context with long pre-defined prefixes to hit a target character size."

    def __init__(
        self,
        weight: int = 1,
        target_chars: int = 4000,
        prefix: Optional[str] = None,
        prefix_type: Optional[ContextFloodingPrefixType] = "enterprise",
    ) -> None:
        super().__init__(weight=weight)
        if target_chars < 200:
            raise ValueError("target_chars must be >= 200")
        self.target_chars = target_chars
        if prefix is not None:
            if not prefix.strip():
                raise ValueError("Prefix cannot be empty.")
            self.prefix = prefix
            self.prefix_type = None
        else:
            if not prefix_type or prefix_type not in DEFAULT_PREFIXES:
                raise ValueError(
                    f"Invalid prefix_type '{prefix_type}'. Valid options are: {list(DEFAULT_PREFIXES)}"
                )
            self.prefix = DEFAULT_PREFIXES[prefix_type]
            self.prefix_type = prefix_type

    def _generate_prefix(self) -> str:
        base = self.prefix.strip()
        expanded = base
        while len(expanded) < self.target_chars:
            expanded += "\n\n" + base
        trimmed = expanded[: self.target_chars]
        if " " in trimmed:
            trimmed = trimmed.rsplit(" ", 1)[0]
        return trimmed

    def transform(self, attack: str) -> str:
        return f"{self._generate_prefix()}\n\n{attack}".strip()
