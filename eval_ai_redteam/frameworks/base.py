"""Safety framework base types (written fresh).

A framework is a static table: risk categories, each bundling the
vulnerabilities (with sub-types) and the attack techniques (with sampling
weights) that probe it. Running a framework means running every
category and reporting pass rates per category.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Optional, Sequence

from ..attacks.base import BaseAttack
from ..vulnerabilities.base import BaseVulnerability


@dataclass
class RiskCategory:
    name: str
    vulnerabilities: list[BaseVulnerability] = field(default_factory=list)
    attacks: list[BaseAttack] = field(default_factory=list)
    description: Optional[str] = None
    _display_name: Optional[str] = None

    @property
    def display_name(self) -> str:
        return self._display_name or self.name


class AISafetyFramework:
    """Subclasses bind ``name``, ``description`` and ``categories_table``."""

    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    categories_table: ClassVar[list[RiskCategory]] = []

    @classmethod
    def get_categories_table(cls) -> list[RiskCategory]:
        """Subclasses may override to load the table lazily."""
        return cls.categories_table

    def __init__(self, categories: Optional[Sequence[str]] = None) -> None:
        table = {c.name: c for c in self.get_categories_table()}
        if categories is None:
            chosen = list(table)
        else:
            unknown = [c for c in categories if c not in table]
            if unknown:
                raise ValueError(
                    f"{self.get_name()}: unknown categories {unknown}; "
                    f"allowed: {list(table)}"
                )
            chosen = list(dict.fromkeys(categories))
        self.categories: list[str] = chosen
        self.risk_categories: list[RiskCategory] = [table[c] for c in chosen]
        self.vulnerabilities: list[BaseVulnerability] = [
            v for c in self.risk_categories for v in c.vulnerabilities
        ]
        self.attacks: list[BaseAttack] = [a for c in self.risk_categories for a in c.attacks]

    @classmethod
    def allowed_categories(cls) -> list[str]:
        return [c.name for c in cls.get_categories_table()]

    def get_name(self) -> str:
        return self.name or self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(categories={self.categories})"
