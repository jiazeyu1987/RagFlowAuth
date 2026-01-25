from __future__ import annotations

"""
Schema bootstrap / additive migrations.

This project historically used a single `schema_migrations.py` file that both created tables
and applied additive schema changes at startup. To keep the codebase maintainable, the
implementation is now split into small modules under `backend/database/schema/`.

Public entrypoints are kept for compatibility:
- `ensure_schema(db_path)` (preferred)
- `ensure_kb_ref_columns(db_path)` (legacy alias)
"""

from pathlib import Path

from backend.database.schema.ensure import ensure_schema as _ensure_schema


def ensure_kb_ref_columns(db_path: str | Path) -> None:
    # Legacy alias; kept because older code/docs call it.
    _ensure_schema(db_path)


def ensure_schema(db_path: str | Path) -> None:
    _ensure_schema(db_path)

