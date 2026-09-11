"""Baseline attack generation schema: ``{"data": [{"input": ...}, ...]}``."""

from __future__ import annotations

from pydantic import BaseModel


class SyntheticData(BaseModel):
    input: str


class SyntheticDataList(BaseModel):
    data: list[SyntheticData]
