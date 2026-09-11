"""Judge response schemas (shared by every vulnerability)."""

from __future__ import annotations

from pydantic import BaseModel


class ReasonScore(BaseModel):
    """Every judge prompt asks for ``{"score": 0 or 1, "reason": ...}``."""

    score: float
    reason: str


class Purpose(BaseModel):
    purpose: str


class Entities(BaseModel):
    entities: list[str]
