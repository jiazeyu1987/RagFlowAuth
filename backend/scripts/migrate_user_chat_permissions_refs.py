from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from backend.database.paths import resolve_auth_db_path

from backend.database.schema_migrations import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.ragflow_connection import create_ragflow_connection
from backend.services.ragflow_chat_service import RagflowChatService


def _resolve_db_path(raw: str | None) -> Path:
    return resolve_auth_db_path(raw)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize user_chat_permissions.chat_id to canonical refs (chat_<id>/agent_<id>)"
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (default: settings.DATABASE_PATH relative to backend/)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print changes, do not write DB")
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db_path)
    ensure_schema(str(db_path))
    conn = connect_sqlite(db_path)
    try:
        if not _table_exists(conn, "user_chat_permissions"):
            print("[SKIP] user_chat_permissions not found")
            return

        ragflow_conn = create_ragflow_connection()
        ragflow = RagflowChatService(connection=ragflow_conn)
        rows = conn.execute(
            "SELECT id, user_id, chat_id FROM user_chat_permissions ORDER BY id"
        ).fetchall()

        changed = 0
        deduped = 0
        for row in rows:
            old = row["chat_id"]
            if not isinstance(old, str) or not old:
                continue
            new = ragflow.normalize_chat_ref(old)
            if new == old:
                continue

            changed += 1
            print(f"[CHANGE] id={row['id']} user_id={row['user_id']} chat_id: {old} -> {new}")
            if args.dry_run:
                continue

            # Update while respecting unique(user_id, chat_id)
            try:
                conn.execute(
                    "UPDATE user_chat_permissions SET chat_id = ? WHERE id = ?",
                    (new, row["id"]),
                )
            except sqlite3.IntegrityError:
                # A row already exists with (user_id, new). Drop this duplicate.
                deduped += 1
                conn.execute("DELETE FROM user_chat_permissions WHERE id = ?", (row["id"],))

        if not args.dry_run:
            conn.commit()

        print(f"[OK] Rows changed: {changed}, duplicates removed: {deduped} (dry_run={args.dry_run})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
