from __future__ import annotations

import json
import logging
from typing import Any

from backend.app.core.config import settings


def permdbg(event: str, **fields: Any) -> None:
    """
    Permission-debug logging that can be toggled via env var.

    - Enable: set `PERMDBG_ENABLED=true`
    - Output: uses `uvicorn.error` logger so it shows up in the same console stream.
    """
    if not getattr(settings, "PERMDBG_ENABLED", False):
        return
    payload = {"event": f"PERMDBG.{event}", **fields}
    try:
        msg = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        msg = str(payload)
    logging.getLogger("uvicorn.error").info(msg)
