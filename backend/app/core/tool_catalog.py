from __future__ import annotations

from typing import Iterable

ASSIGNABLE_TOOL_IDS: tuple[str, ...] = (
    "paper_download",
    "patent_download",
    "package_drawing",
    "nhsa_code_search",
    "shanghai_tax",
    "drug_admin",
    "nmpa",
)

ADMIN_ONLY_TOOL_IDS: frozenset[str] = frozenset({"nas_browser"})

ALL_TOOL_IDS: frozenset[str] = frozenset(ASSIGNABLE_TOOL_IDS) | ADMIN_ONLY_TOOL_IDS

_ASSIGNABLE_TOOL_ID_SET: frozenset[str] = frozenset(ASSIGNABLE_TOOL_IDS)


def normalize_assignable_tool_ids(raw: Iterable[object] | None) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw or ():
        value = str(item or "").strip()
        if not value:
            continue
        if value not in _ASSIGNABLE_TOOL_ID_SET:
            raise ValueError(f"invalid_tool_id:{value}")
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized
