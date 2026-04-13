from __future__ import annotations

from datetime import date
import time
from typing import Any
from uuid import uuid4


class GovernanceClosureError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def require_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise GovernanceClosureError(f"{field_name}_required", status_code=400)
    return text


def optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def require_known_value(value: Any, *, field_name: str, allowed: set[str]) -> str:
    text = str(value or "").strip().lower()
    if text not in allowed:
        raise GovernanceClosureError(f"invalid_{field_name}", status_code=400)
    return text


def require_positive_ms(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except Exception as exc:
        raise GovernanceClosureError(f"invalid_{field_name}", status_code=400) from exc
    if parsed <= 0:
        raise GovernanceClosureError(f"invalid_{field_name}", status_code=400)
    return parsed


def validate_iso_date(value: Any, *, field_name: str) -> str:
    text = require_text(value, field_name)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise GovernanceClosureError(f"invalid_{field_name}", status_code=400) from exc
    return text


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
