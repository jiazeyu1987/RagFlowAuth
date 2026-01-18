from __future__ import annotations

from pathlib import Path


def backend_root() -> Path:
    # backend/app/core/paths.py -> backend
    return Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return backend_root().parent


def resolve_backend_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return backend_root() / p

