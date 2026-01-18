from __future__ import annotations

from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.paths import resolve_backend_path


def resolve_auth_db_path(db_path: str | Path | None = None) -> Path:
    """
    Resolve auth.db path consistently across runtime + scripts.

    - When db_path is relative, it's resolved relative to backend/ (via resolve_backend_path()).
    - When db_path is None, uses settings.DATABASE_PATH.
    """
    raw = db_path if db_path is not None else settings.DATABASE_PATH
    return resolve_backend_path(raw)
