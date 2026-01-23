from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.database.sqlite import connect_sqlite


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    rows = cur.fetchall()
    return {row[1] for row in rows if row and len(row) > 1}


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_sql: str) -> None:
    # column_sql like: "kb_dataset_id TEXT"
    col_name = column_sql.split()[0].strip()
    if col_name in _columns(conn, table_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def _ensure_download_logs_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "download_logs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS download_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            kb_id TEXT NOT NULL,
            kb_dataset_id TEXT,
            kb_name TEXT,
            downloaded_by TEXT NOT NULL,
            downloaded_at_ms INTEGER NOT NULL,
            ragflow_doc_id TEXT,
            is_batch INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_kb ON download_logs(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_kb_dataset_id ON download_logs(kb_dataset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_time ON download_logs(downloaded_at_ms)")


def _ensure_deletion_logs_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "deletion_logs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deletion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            kb_id TEXT NOT NULL,
            kb_dataset_id TEXT,
            kb_name TEXT,
            deleted_by TEXT NOT NULL,
            deleted_at_ms INTEGER NOT NULL,
            original_uploader TEXT,
            original_reviewer TEXT,
            ragflow_doc_id TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_kb ON deletion_logs(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_kb_dataset_id ON deletion_logs(kb_dataset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_time ON deletion_logs(deleted_at_ms)")


def _ensure_permission_groups_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "permission_groups"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS permission_groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_system INTEGER DEFAULT 0,
            accessible_kbs TEXT DEFAULT '[]',
            accessible_chats TEXT DEFAULT '[]',
            can_upload INTEGER DEFAULT 0,
            can_review INTEGER DEFAULT 0,
            can_download INTEGER DEFAULT 1,
            can_delete INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _ensure_user_permission_groups_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "user_permission_groups"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_permission_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            created_at_ms INTEGER NOT NULL,
            UNIQUE(user_id, group_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_upg_user_id ON user_permission_groups(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_upg_group_id ON user_permission_groups(group_id)")


def _ensure_data_security_settings_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "data_security_settings"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_security_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_minutes INTEGER NOT NULL DEFAULT 1440,
            target_mode TEXT NOT NULL DEFAULT 'share',
            target_ip TEXT,
            target_share_name TEXT,
            target_subdir TEXT,
            target_local_dir TEXT,
            ragflow_compose_path TEXT,
            ragflow_project_name TEXT,
            ragflow_stop_services INTEGER NOT NULL DEFAULT 0,
            auth_db_path TEXT NOT NULL DEFAULT 'data/auth.db',
            updated_at_ms INTEGER NOT NULL DEFAULT 0,
            last_run_at_ms INTEGER
        )
        """
    )
    conn.execute("INSERT OR IGNORE INTO data_security_settings (id) VALUES (1)")


def _add_full_backup_columns_to_data_security(conn: sqlite3.Connection) -> None:
    """Add full backup columns to data_security_settings table"""
    if not _table_exists(conn, "data_security_settings"):
        return
    _add_column_if_missing(conn, "data_security_settings", "full_backup_enabled INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "data_security_settings", "full_backup_include_images INTEGER NOT NULL DEFAULT 1")


def _ensure_backup_jobs_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "backup_jobs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            message TEXT,
            detail TEXT,
            output_dir TEXT,
            created_at_ms INTEGER NOT NULL,
            started_at_ms INTEGER,
            finished_at_ms INTEGER
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backup_jobs_created ON backup_jobs(created_at_ms)")


def _backfill_user_permission_groups_from_users_group_id(conn: sqlite3.Connection) -> None:
    """
    Final deprecation path: ensure multi-group table is the source of truth.

    If legacy users.group_id is populated, backfill it into user_permission_groups.
    Safe to call repeatedly.
    """
    if not _table_exists(conn, "users") or not _table_exists(conn, "user_permission_groups"):
        return
    cols = _columns(conn, "users")
    if "group_id" not in cols:
        return

    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
            SELECT user_id, group_id, COALESCE(created_at_ms, 0)
            FROM users
            WHERE group_id IS NOT NULL
            """
        )
    except Exception:
        # Best-effort only; do not block startup on legacy backfill failures.
        return


def _ensure_users_group_id_column(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "users"):
        return
    cols = _columns(conn, "users")
    if "group_id" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN group_id INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_group_id ON users(group_id)")


def _ensure_users_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "users"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL DEFAULT 'viewer',
            group_id INTEGER,
            status TEXT NOT NULL DEFAULT 'active',
            created_at_ms INTEGER NOT NULL,
            last_login_at_ms INTEGER,
            created_by TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_group_id ON users(group_id)")


def _ensure_kb_documents_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "kb_documents"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kb_documents (
            doc_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            uploaded_at_ms INTEGER NOT NULL,
            reviewed_by TEXT,
            reviewed_at_ms INTEGER,
            review_notes TEXT,
            ragflow_doc_id TEXT,
            kb_id TEXT NOT NULL DEFAULT '展厅',
            kb_dataset_id TEXT,
            kb_name TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_status ON kb_documents(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb ON kb_documents(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_dataset_id ON kb_documents(kb_dataset_id)")


def _ensure_chat_sessions_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "chat_sessions"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_at_ms INTEGER,
            deleted_by TEXT,
            UNIQUE(session_id, chat_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_session ON chat_sessions(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_chat ON chat_sessions(chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_deleted ON chat_sessions(is_deleted)")


def _seed_default_permission_groups(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "permission_groups"):
        return
    cur = conn.execute("SELECT COUNT(*) FROM permission_groups")
    row = cur.fetchone()
    if not row or row[0] != 0:
        return

    conn.executemany(
        """
        INSERT INTO permission_groups (
            group_name, description, is_system,
            accessible_kbs, accessible_chats,
            can_upload, can_review, can_download, can_delete,
            created_at, updated_at
        ) VALUES (?, ?, ?, '[]', '[]', ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        [
            ("admin", "System administrator", 1, 1, 1, 1, 1),
            ("reviewer", "Document reviewer", 0, 0, 1, 1, 0),
            ("operator", "Uploader/operator", 0, 1, 0, 1, 1),
            ("viewer", "Viewer", 0, 0, 0, 1, 0),
            ("guest", "Guest", 0, 0, 0, 0, 0),
        ],
    )


def ensure_kb_ref_columns(db_path: str | Path) -> None:
    """
    Ensure baseline schema and stage-3 KB ref columns exist.

    Safe to call repeatedly; no-op when schema already exists.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect_sqlite(db_path)
    try:
        _ensure_users_table(conn)
        _ensure_kb_documents_table(conn)
        _ensure_chat_sessions_table(conn)

        _ensure_permission_groups_table(conn)
        _ensure_user_permission_groups_table(conn)
        _ensure_users_group_id_column(conn)
        _seed_default_permission_groups(conn)
        _backfill_user_permission_groups_from_users_group_id(conn)

        _ensure_data_security_settings_table(conn)
        _ensure_backup_jobs_table(conn)
        _add_full_backup_columns_to_data_security(conn)

        _ensure_download_logs_table(conn)
        _ensure_deletion_logs_table(conn)

        for table_name in ("kb_documents", "deletion_logs", "download_logs"):
            if not _table_exists(conn, table_name):
                continue
            _add_column_if_missing(conn, table_name, "kb_dataset_id TEXT")
            _add_column_if_missing(conn, table_name, "kb_name TEXT")

            # Best-effort: keep old data queryable by name
            existing = _columns(conn, table_name)
            if "kb_id" in existing and "kb_name" in existing:
                conn.execute(
                    f"UPDATE {table_name} SET kb_name = kb_id WHERE (kb_name IS NULL OR kb_name = '')"
                )

        if _table_exists(conn, "deletion_logs"):
            _add_column_if_missing(conn, "deletion_logs", "action TEXT")
            _add_column_if_missing(conn, "deletion_logs", "ragflow_deleted INTEGER")
            _add_column_if_missing(conn, "deletion_logs", "ragflow_delete_error TEXT")

        if _table_exists(conn, "kb_documents"):
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_dataset_id ON kb_documents(kb_dataset_id)")
        if _table_exists(conn, "deletion_logs"):
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_kb_dataset_id ON deletion_logs(kb_dataset_id)")
        if _table_exists(conn, "download_logs"):
            conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_kb_dataset_id ON download_logs(kb_dataset_id)")

        conn.commit()
    finally:
        conn.close()


def ensure_schema(db_path: str | Path) -> None:
    """
    Canonical schema-ensure entrypoint (preferred name).
    """
    ensure_kb_ref_columns(db_path)
