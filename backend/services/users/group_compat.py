from __future__ import annotations

from typing import Iterable


def normalize_legacy_group_ids(
    *,
    group_ids: Iterable[int] | None = None,
    group_id: int | None = None,
) -> list[int]:
    raw_values = list(group_ids or [])
    if not raw_values and group_id is not None:
        raw_values = [group_id]

    seen: set[int] = set()
    normalized: list[int] = []
    for raw_value in raw_values:
        if raw_value is None:
            continue
        value = int(raw_value)
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def primary_group_id(group_ids: Iterable[int] | None = None) -> int | None:
    normalized = normalize_legacy_group_ids(group_ids=group_ids)
    return normalized[0] if normalized else None
