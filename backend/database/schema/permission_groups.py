from __future__ import annotations

import json
import sqlite3
import time

from backend.app.core.tool_catalog import ASSIGNABLE_TOOL_IDS

from .helpers import add_column_if_missing, table_exists, columns


def ensure_permission_groups_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "permission_groups"):
        ensure_permission_groups_columns(conn)
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS permission_groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_system INTEGER DEFAULT 0,
            created_by TEXT,
            folder_id TEXT,
            accessible_kbs TEXT DEFAULT '[]',
            accessible_kb_nodes TEXT DEFAULT '[]',
            accessible_chats TEXT DEFAULT '[]',
            accessible_tools TEXT DEFAULT '[]',
            can_upload INTEGER DEFAULT 0,
            can_review INTEGER DEFAULT 0,
            can_download INTEGER DEFAULT 1,
            can_copy INTEGER DEFAULT 0,
            can_delete INTEGER DEFAULT 0,
            can_manage_kb_directory INTEGER DEFAULT 0,
            can_view_kb_config INTEGER DEFAULT 1,
            can_view_tools INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_permission_groups_columns(conn)


def ensure_permission_groups_columns(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "permission_groups"):
        return
    add_column_if_missing(conn, "permission_groups", "created_by TEXT")
    add_column_if_missing(conn, "permission_groups", "folder_id TEXT")
    add_column_if_missing(conn, "permission_groups", "accessible_kb_nodes TEXT DEFAULT '[]'")
    add_column_if_missing(conn, "permission_groups", "accessible_tools TEXT DEFAULT '[]'")
    add_column_if_missing(conn, "permission_groups", "can_manage_kb_directory INTEGER DEFAULT 0")
    add_column_if_missing(conn, "permission_groups", "can_view_kb_config INTEGER DEFAULT 1")
    add_column_if_missing(conn, "permission_groups", "can_view_tools INTEGER DEFAULT 1")
    add_column_if_missing(conn, "permission_groups", "can_copy INTEGER DEFAULT 0")


def ensure_user_permission_groups_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "user_permission_groups"):
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


def ensure_user_tool_permissions_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "user_tool_permissions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_tool_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                granted_by_user_id TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                UNIQUE(user_id, tool_id)
            )
            """
        )
    cols = columns(conn, "user_tool_permissions")
    if "granted_by_user_id" not in cols:
        add_column_if_missing(conn, "user_tool_permissions", "granted_by_user_id TEXT")
    if "updated_at_ms" not in cols:
        add_column_if_missing(conn, "user_tool_permissions", "updated_at_ms INTEGER NOT NULL DEFAULT 0")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_utp_user_id ON user_tool_permissions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_utp_tool_id ON user_tool_permissions(tool_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_utp_granted_by ON user_tool_permissions(granted_by_user_id)")


def seed_default_permission_groups(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "permission_groups"):
        return
    cur = conn.execute("SELECT COUNT(*) FROM permission_groups")
    row = cur.fetchone()
    if not row or row[0] != 0:
        return

    conn.executemany(
        """
        INSERT INTO permission_groups (
            group_name, description, is_system, created_by,
            accessible_kbs, accessible_chats, accessible_tools,
            can_upload, can_review, can_download, can_copy, can_delete, can_manage_kb_directory,
            can_view_kb_config, can_view_tools,
            created_at, updated_at
        ) VALUES (?, ?, ?, NULL, '[]', '[]', '[]', ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        [
            ("admin", "System administrator", 1, 1, 1, 1, 1, 1, 1, 1, 1),
            ("reviewer", "Document reviewer", 0, 0, 1, 1, 0, 0, 0, 1, 1),
            ("operator", "Uploader/operator", 0, 1, 0, 1, 0, 1, 0, 1, 1),
            ("viewer", "Viewer", 0, 0, 0, 1, 0, 0, 0, 1, 1),
            ("guest", "Guest", 0, 0, 0, 0, 0, 0, 0, 1, 1),
        ],
    )


def backfill_user_permission_groups_from_users_group_id(conn: sqlite3.Connection) -> None:
    """
    Final deprecation path: ensure multi-group table is the source of truth.

    If legacy users.group_id is populated, backfill it into user_permission_groups.
    Safe to call repeatedly.
    """
    if not table_exists(conn, "users") or not table_exists(conn, "user_permission_groups"):
        return
    cols = columns(conn, "users")
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
        return


def _normalize_legacy_group_tool_ids(*, can_view_tools: object, accessible_tools: object) -> set[str]:
    if not bool(can_view_tools):
        return set()
    if accessible_tools is None:
        return set(ASSIGNABLE_TOOL_IDS)

    try:
        raw = json.loads(str(accessible_tools or "[]"))
    except Exception as exc:
        raise ValueError("tool_migration_invalid_accessible_tools_json") from exc

    if not isinstance(raw, list):
        raise ValueError("tool_migration_invalid_accessible_tools_json")
    if not raw:
        return set(ASSIGNABLE_TOOL_IDS)

    allowed = set(ASSIGNABLE_TOOL_IDS)
    normalized: set[str] = set()
    for item in raw:
        tool_id = str(item or "").strip()
        if not tool_id:
            continue
        if tool_id not in allowed:
            raise ValueError(f"tool_migration_invalid_tool_id:{tool_id}")
        normalized.add(tool_id)
    return normalized


def migrate_user_tools_from_permission_groups(conn: sqlite3.Connection) -> None:
    if (
        not table_exists(conn, "users")
        or not table_exists(conn, "permission_groups")
        or not table_exists(conn, "user_permission_groups")
        or not table_exists(conn, "user_tool_permissions")
    ):
        return

    existing = conn.execute("SELECT COUNT(*) FROM user_tool_permissions").fetchone()
    if existing and int(existing[0] or 0) > 0:
        return

    user_rows = conn.execute(
        """
        SELECT user_id, role, manager_user_id
        FROM users
        """
    ).fetchall()
    if not user_rows:
        return

    user_meta: dict[str, tuple[str, str | None]] = {}
    for row in user_rows:
        user_id = str(row[0] or "").strip()
        if not user_id:
            continue
        role = str(row[1] or "").strip().lower()
        manager_user_id = str(row[2] or "").strip() or None
        user_meta[user_id] = (role, manager_user_id)

    tool_rows = conn.execute(
        """
        SELECT upg.user_id, pg.can_view_tools, pg.accessible_tools
        FROM user_permission_groups upg
        JOIN permission_groups pg ON pg.group_id = upg.group_id
        """
    ).fetchall()
    derived: dict[str, set[str]] = {}
    for row in tool_rows:
        user_id = str(row[0] or "").strip()
        if not user_id or user_id not in user_meta:
            continue
        current = derived.setdefault(user_id, set())
        current.update(
            _normalize_legacy_group_tool_ids(
                can_view_tools=row[1],
                accessible_tools=row[2],
            )
        )

    for user_id, tool_ids in derived.items():
        if not tool_ids:
            continue
        role, manager_user_id = user_meta[user_id]
        if role == "admin":
            continue
        if role == "sub_admin":
            continue
        if role == "viewer":
            # Legacy databases may contain unmanaged viewers created before the
            # current sub-admin ownership model existed. Keep their derived
            # tool permissions migratable instead of blocking startup.
            if not manager_user_id:
                continue
            manager_meta = user_meta.get(manager_user_id)
            if not manager_meta or manager_meta[0] != "sub_admin":
                continue
            manager_tools = derived.get(manager_user_id, set())
            if not tool_ids.issubset(manager_tools):
                continue
            continue
        raise ValueError(f"tool_migration_role_not_supported:{role}:{user_id}")

    now_ms = int(time.time() * 1000)
    for user_id, tool_ids in sorted(derived.items()):
        if not tool_ids:
            continue
        role, manager_user_id = user_meta[user_id]
        if role not in {"sub_admin", "viewer"}:
            continue
        # Default to a system migration grant for legacy users that do not fit
        # the current managed-viewer invariant; preserve a manager grant only
        # when the relationship is valid and the viewer scope is bounded.
        granted_by_user_id = "system_migration"
        if role == "viewer" and manager_user_id:
            manager_meta = user_meta.get(manager_user_id)
            manager_tools = derived.get(manager_user_id, set())
            if manager_meta and manager_meta[0] == "sub_admin" and tool_ids.issubset(manager_tools):
                granted_by_user_id = manager_user_id
        for tool_id in sorted(tool_ids):
            conn.execute(
                """
                INSERT INTO user_tool_permissions (
                    user_id, tool_id, granted_by_user_id, created_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, tool_id, granted_by_user_id, now_ms, now_ms),
            )
