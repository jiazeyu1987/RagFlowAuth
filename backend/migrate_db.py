from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.database.schema_migrations import ensure_schema
from backend.database.sqlite import connect_sqlite


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    try:
        cur = conn.execute(f"PRAGMA table_info({table_name})")
    except sqlite3.OperationalError:
        return set()
    rows = cur.fetchall()
    return {row[1] for row in rows if row and len(row) > 1}


def migrate_database(old_db_path: Path, new_db_path: Path | None = None) -> bool:
    """
    Migrate data from an old auth.db into the current schema.

    Notes:
    - Uses database.schema_migrations.ensure_schema() to create/upgrade the destination schema.
    - Does NOT treat legacy users.group_id as authoritative; it assigns user_permission_groups based on role.
    """
    if not old_db_path.exists():
        print(f"[ERROR] Old database not found: {old_db_path}")
        return False

    if new_db_path is None:
        new_db_path = old_db_path

    backup_path = old_db_path.with_suffix(old_db_path.suffix + ".backup")
    print(f"[INFO] Backup: {backup_path}")
    backup_path.write_bytes(old_db_path.read_bytes())

    print("[INFO] Ensuring destination schema...")
    ensure_schema(str(new_db_path))

    old_conn = connect_sqlite(old_db_path)
    new_conn = connect_sqlite(new_db_path)

    try:
        old_cur = old_conn.cursor()
        new_cur = new_conn.cursor()

        if not _table_exists(old_conn, "users"):
            print("[SKIP] users table not found in old DB")
            return True

        role_to_group_id: dict[str, int] = {}
        if _table_exists(new_conn, "permission_groups"):
            rows = new_cur.execute("SELECT group_id, group_name FROM permission_groups").fetchall()
            for row in rows:
                name = row["group_name"]
                if isinstance(name, str) and name:
                    role_to_group_id[name] = int(row["group_id"])

        print("[INFO] Migrating users...")
        users = old_cur.execute("SELECT * FROM users").fetchall()
        old_user_cols = _columns(old_conn, "users")

        for user in users:
            user_id = user["user_id"]
            username = user["username"]
            password_hash = user["password_hash"]
            email = user["email"] if "email" in old_user_cols else None
            role = user["role"] if "role" in old_user_cols else "viewer"
            status = user["status"] if "status" in old_user_cols else "active"
            created_at_ms = int(user["created_at_ms"]) if "created_at_ms" in old_user_cols else 0
            last_login_at_ms = user["last_login_at_ms"] if "last_login_at_ms" in old_user_cols else None
            created_by = user["created_by"] if "created_by" in old_user_cols else None

            new_cur.execute(
                """
                INSERT OR REPLACE INTO users (
                    user_id, username, password_hash, email, role, group_id, status,
                    created_at_ms, last_login_at_ms, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    password_hash,
                    email,
                    role,
                    None,
                    status,
                    created_at_ms,
                    last_login_at_ms,
                    created_by,
                ),
            )

            gid = role_to_group_id.get(role)
            if gid is not None and _table_exists(new_conn, "user_permission_groups"):
                new_cur.execute(
                    """
                    INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, gid, created_at_ms),
                )

        print(f"[OK] Users migrated: {len(users)}")

        if _table_exists(old_conn, "kb_documents"):
            print("[INFO] Migrating kb_documents...")
            docs = old_cur.execute("SELECT * FROM kb_documents").fetchall()
            old_doc_cols = _columns(old_conn, "kb_documents")
            for doc in docs:
                kb_id = doc["kb_id"] if "kb_id" in old_doc_cols else "展厅"
                kb_dataset_id = doc["kb_dataset_id"] if "kb_dataset_id" in old_doc_cols else None
                kb_name = doc["kb_name"] if "kb_name" in old_doc_cols else None

                new_cur.execute(
                    """
                    INSERT OR REPLACE INTO kb_documents (
                        doc_id, filename, file_path, file_size, mime_type,
                        uploaded_by, status, uploaded_at_ms, reviewed_by,
                        reviewed_at_ms, review_notes, ragflow_doc_id,
                        kb_id, kb_dataset_id, kb_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc["doc_id"],
                        doc["filename"],
                        doc["file_path"],
                        doc["file_size"],
                        doc["mime_type"],
                        doc["uploaded_by"],
                        doc["status"] if "status" in old_doc_cols else "pending",
                        doc["uploaded_at_ms"],
                        doc["reviewed_by"] if "reviewed_by" in old_doc_cols else None,
                        doc["reviewed_at_ms"] if "reviewed_at_ms" in old_doc_cols else None,
                        doc["review_notes"] if "review_notes" in old_doc_cols else None,
                        doc["ragflow_doc_id"] if "ragflow_doc_id" in old_doc_cols else None,
                        kb_id,
                        kb_dataset_id,
                        kb_name or kb_id,
                    ),
                )
            print(f"[OK] kb_documents migrated: {len(docs)}")
        else:
            print("[SKIP] kb_documents table not found in old DB")

        new_conn.commit()
        print(f"[DONE] DB: {new_db_path}")
        return True
    finally:
        old_conn.close()
        new_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate old auth.db into current schema")
    parser.add_argument("--old-db", required=True, help="Old auth.db path (backend-relative if not absolute)")
    parser.add_argument("--new-db", default=None, help="New auth.db path (default: overwrite old db)")
    args = parser.parse_args()

    old_db = resolve_auth_db_path(args.old_db)
    new_db = resolve_auth_db_path(args.new_db) if args.new_db else None

    ok = migrate_database(old_db, new_db)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
