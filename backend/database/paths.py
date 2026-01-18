from __future__ import annotations

from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.paths import resolve_repo_path


def resolve_auth_db_path(db_path: str | Path | None = None) -> Path:
    """
    Resolve auth.db path consistently across runtime + scripts.

    - When db_path is relative, it's resolved relative to repo root (the parent of `backend/`).
    """
    raw = db_path if db_path is not None else settings.DATABASE_PATH
    p = Path(raw)
    if p.is_absolute():
        return p

    return resolve_repo_path(p)
