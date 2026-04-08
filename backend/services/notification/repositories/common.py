from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

ConnectFactory = Callable[[], Any]


def to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def from_json_text(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)
