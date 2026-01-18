#!/usr/bin/env python3
"""
增强型权限组脚本（兼容历史脚本名）

目标：
- 统一到当前项目的“权限组（resolver）为准”的模型；
- 使用 database.schema_migrations.ensure_schema() 作为唯一建表/升级入口；
- 不再写入/依赖 users.group_id（已废弃），而是写入 user_permission_groups 关系表。

执行方式：
    python -m backend.scripts.migrate_to_enhanced_permission_groups --db-path data/auth.db
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.database.schema_migrations import ensure_schema
from backend.database.sqlite import connect_sqlite


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
        print(f"[ERROR] 数据库文件不存在: {db_path}")
        return False

    ensure_schema(str(db_path))

    conn = connect_sqlite(db_path)
    try:
        if not _table_exists(conn, "users"):
            print("[SKIP] users 表不存在")
            return True
        if not _table_exists(conn, "permission_groups") or not _table_exists(conn, "user_permission_groups"):
            print("[ERROR] permission_groups/user_permission_groups 表不存在（schema ensure 失败）")
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

        print(f"[OK] 完成: 处理 {len(users)} 个用户，写入关系（尝试）{changed} 条 (dry_run={dry_run})")
        return True
    except Exception as e:
        if not dry_run:
            conn.rollback()
        print(f"[ERROR] 迁移失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate/seed enhanced permission groups (resolver-first)")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (default: settings.DATABASE_PATH relative to backend/)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print changes, do not write DB")
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db_path)
    ok = migrate_database(db_path, dry_run=bool(args.dry_run))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
