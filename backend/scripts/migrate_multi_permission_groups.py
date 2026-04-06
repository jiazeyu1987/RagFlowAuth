"""
Deprecated maintenance wrapper for multi-permission-group bootstrap.

The canonical schema bootstrap now lives in
`backend.database.schema.ensure.ensure_schema()`, and `ensure_database()`
already applies the legacy `users.group_id` backfill into
`user_permission_groups`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.runtime.runner import ensure_database


def _resolve_db_path(raw: str | None) -> Path:
    return resolve_auth_db_path(raw)


def migrate(db_path: Path) -> None:
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        return

    ensure_database(db_path=db_path)
    print("[OK] Schema ensured (includes user_permission_groups backfill)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ensure DB supports multi permission groups per user")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (relative paths are resolved from repo root)",
    )
    args = parser.parse_args()

    migrate(_resolve_db_path(args.db_path))
