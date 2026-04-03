from __future__ import annotations

from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.paths import repo_root, resolve_repo_path


LEGACY_AUTH_DB_RELATIVE_PATH = Path("backend/data/auth.db")


def _is_legacy_auth_db_path(path: Path) -> bool:
    legacy_abs = (repo_root() / LEGACY_AUTH_DB_RELATIVE_PATH).resolve()
    try:
        candidate = path.resolve()
    except OSError:
        candidate = path.absolute()
    return candidate == legacy_abs


def resolve_auth_db_path(db_path: str | Path | None = None) -> Path:
    """
    Resolve auth.db path consistently across runtime + scripts.

    - When db_path is relative, it's resolved relative to repo root (the parent of `backend/`).
    """
    raw = db_path if db_path is not None else settings.DATABASE_PATH
    p = Path(raw)
    resolved = p if p.is_absolute() else resolve_repo_path(p)
    if _is_legacy_auth_db_path(resolved):
        raise ValueError(
            "legacy_auth_db_path_not_supported: backend/data/auth.db has been retired, use data/auth.db"
        )
    return resolved
