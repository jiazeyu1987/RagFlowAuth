"""
DEPRECATED:
多权限组表结构 + legacy users.group_id backfill 已由
`backend.database.schema_migrations.ensure_schema()` 统一接管。
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
    print("[OK] Schema ensured (includes user_permission_groups + legacy group_id backfill)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate DB to support multi permission groups per user")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (relative paths are resolved from repo root)",
    )
    args = parser.parse_args()

    migrate(_resolve_db_path(args.db_path))
