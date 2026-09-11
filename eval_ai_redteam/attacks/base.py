"""Attack technique base types (written fresh)."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Optional


class Exploitability(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BaseAttack:
    """A technique that turns a baseline attack into a stronger one.

    ``weight`` is the sampling weight when the engine picks one technique
    per test case from a list (deepteam semantics). ``multi_turn`` marks
    techniques that drive a whole conversation instead of rewriting one
    prompt.
    """

    name: ClassVar[str] = ""
    description: ClassVar[Optional[str]] = None
    exploitability: ClassVar[Exploitability] = Exploitability.MEDIUM
    multi_turn: ClassVar[bool] = False

    def __init__(self, weight: int = 1) -> None:
        if weight < 0:
            raise ValueError("weight must be >= 0")
        self.weight = weight

    def get_name(self) -> str:
        return self.name or self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(weight={self.weight})"
