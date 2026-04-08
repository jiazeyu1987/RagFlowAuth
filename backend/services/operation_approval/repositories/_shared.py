from __future__ import annotations

import json


def to_json_text(value) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def from_json_text(value: str | None):
    if not value:
        return {}
    return json.loads(value)


def coerce_ms(value: int | None) -> int | None:
    if value is None:
        return None
    return int(value)
