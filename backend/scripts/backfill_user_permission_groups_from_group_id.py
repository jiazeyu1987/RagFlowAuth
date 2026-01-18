from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

from backend.database.paths import resolve_auth_db_path

from backend.database.schema_migrations import ensure_schema
from backend.database.sqlite import connect_sqlite


def _resolve_db_path(raw: str | None) -> Path:
    return resolve_auth_db_path(raw)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill user_permission_groups from legacy users.group_id (legacy compat only)",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (default: settings.DATABASE_PATH relative to backend/)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print changes, do not write DB")
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db_path)

    # ensure_schema() already contains best-effort legacy backfill, but do not mutate DB on --dry-run.
    if not args.dry_run:
        ensure_schema(str(db_path))

    conn = connect_sqlite(db_path)
    try:
        if not _table_exists(conn, "users"):
            print("[ERROR] users table not found")
            return

        if not _table_exists(conn, "user_permission_groups"):
            print("[ERROR] user_permission_groups table not found (run ensure_schema first)")
            return

        now_ms = int(time.time() * 1000)
        cur = conn.execute(
            "SELECT user_id, group_id FROM users WHERE group_id IS NOT NULL"
        )
        rows = cur.fetchall()
        if not rows:
            print("[OK] No users with legacy group_id")
            return

        changed = 0
        for row in rows:
            user_id = row["user_id"]
            group_id = row["group_id"]
            if not user_id or group_id is None:
                continue

            exists = conn.execute(
                "SELECT 1 FROM user_permission_groups WHERE user_id = ? AND group_id = ? LIMIT 1",
                (user_id, group_id),
            ).fetchone()
            if exists:
                continue

            changed += 1
            print(f"[ADD] user_id={user_id} group_id={group_id}")
            if not args.dry_run:
                conn.execute(
                    "INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms) VALUES (?, ?, ?)",
                    (user_id, group_id, now_ms),
                )

        if not args.dry_run:
            conn.commit()
        print(f"[OK] Rows inserted: {changed} (dry_run={args.dry_run})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
