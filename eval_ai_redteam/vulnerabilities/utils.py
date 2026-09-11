"""Type validation helpers for vulnerability constructors."""

from __future__ import annotations

from enum import Enum
from typing import Optional, Sequence


def resolve_types(
    vulnerability_name: str,
    types: Optional[Sequence[str | Enum]],
    allowed: type[Enum],
) -> list[Enum]:
    """Turn user-supplied type names into enum members, in enum order.

    ``None`` means "every type". Unknown names, duplicates and an empty
    list raise ``ValueError`` with the allowed values spelled out.
    """
    if types is None:
        return list(allowed)
    if not isinstance(types, (list, tuple)):
        raise TypeError(
            f"The 'types' attribute for the {vulnerability_name} vulnerability "
            "must be a list of strings."
        )
    if len(types) == 0:
        raise ValueError(
            f"The 'types' attribute for the {vulnerability_name} vulnerability "
            "cannot be an empty list."
        )
    wanted: list[str] = [t.value if isinstance(t, Enum) else str(t) for t in types]
    duplicates = sorted({t for t in wanted if wanted.count(t) > 1})
    if duplicates:
        raise ValueError(
            f"Duplicate types detected for the {vulnerability_name} vulnerability: "
            + ", ".join(f'"{d}"' for d in duplicates)
        )
    valid = [member.value for member in allowed]
    invalid = [t for t in wanted if t not in valid]
    if invalid:
        raise ValueError(
            f"Unknown type(s) for the {vulnerability_name} vulnerability: "
            + ", ".join(f'"{t}"' for t in invalid)
            + ". Available types: "
            + ", ".join(f'"{v}"' for v in valid)
        )
    return [member for member in allowed if member.value in wanted]
