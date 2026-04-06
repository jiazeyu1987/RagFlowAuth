#!/usr/bin/env python3
"""
Seed resolver-first permission group relations for an existing auth DB.

This script keeps the historical command name, but the schema bootstrap is
owned by `backend.database.schema.ensure.ensure_schema()` via
`backend.runtime.runner.ensure_database()`.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite
from backend.runtime.runner import ensure_database


def _resolve_db_path(raw: str | None) -> Path:
    return resolve_auth_db_path(raw)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def migrate_database(db_path: Path, *, dry_run: bool = False) -> bool:
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        return False

    ensure_database(db_path=db_path)

    conn = connect_sqlite(db_path)
    try:
        if not _table_exists(conn, "users"):
            print("[SKIP] users table not found")
            return True
        if not _table_exists(conn, "permission_groups") or not _table_exists(conn, "user_permission_groups"):
            print("[ERROR] permission_groups/user_permission_groups table not found after schema ensure")
            return False

        role_to_group_id: dict[str, int] = {}
        for row in conn.execute("SELECT group_id, group_name FROM permission_groups").fetchall():
            name = row["group_name"]
            if isinstance(name, str) and name:
                role_to_group_id[name] = int(row["group_id"])

        users = conn.execute("SELECT user_id, role, created_at_ms FROM users").fetchall()
        changed = 0
        for user in users:
            role = user["role"] or "viewer"
            group_id = role_to_group_id.get(role)
            if group_id is None:
                continue

            user_id = user["user_id"]
            created_at_ms = int(user["created_at_ms"] or 0)

            changed += 1
            print(f"[MAP] user_id={user_id} role={role} -> group_id={group_id}")
            if dry_run:
                continue

            conn.execute(
                """
                INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
                VALUES (?, ?, ?)
                """,
                (user_id, group_id, created_at_ms),
            )

        if not dry_run:
            conn.commit()

        print(f"[OK] Processed {len(users)} users; attempted relation writes={changed} (dry_run={dry_run})")
        return True
    except Exception as exc:
        if not dry_run:
            conn.rollback()
        print(f"[ERROR] Migration failed: {exc}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed enhanced permission groups (resolver-first)")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (relative paths are resolved from repo root)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print changes, do not write DB")
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db_path)
    ok = migrate_database(db_path, dry_run=bool(args.dry_run))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
