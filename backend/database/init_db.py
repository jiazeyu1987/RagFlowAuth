from __future__ import annotations

import hashlib
import time
import uuid

from backend.database.paths import resolve_auth_db_path
from backend.database.schema_migrations import ensure_schema
from backend.database.sqlite import connect_sqlite

def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def init_database(db_path: str = None):
    """
    Initialize SQLite database with new schema (no user_sessions or auth_audit tables).

    Args:
        db_path: Path to database file. If None, uses default path.
    """
    resolved_db_path = resolve_auth_db_path(db_path)
    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create/upgrade schema (idempotent).
    ensure_schema(str(resolved_db_path))

    conn = connect_sqlite(resolved_db_path)
    cursor = conn.cursor()

    # Note: schema is ensured by database.schema_migrations.ensure_schema().

    # Create default admin user if not exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        admin_user_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        cursor.execute("SELECT group_id FROM permission_groups WHERE group_name = 'admin' LIMIT 1")
        row = cursor.fetchone()
        admin_group_id = row[0] if row else None

        cursor.execute("""
            INSERT INTO users (
                user_id, username, password_hash, email, role, group_id, status,
                created_at_ms, last_login_at_ms, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            admin_user_id,
            "admin",
            hash_password("admin123"),
            "admin@example.com",
            "admin",
            None,
            "active",
            now_ms,
            None,
            "system"
        ))

        if admin_group_id is not None:
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
                VALUES (?, ?, ?)
                """,
                (admin_user_id, admin_group_id, now_ms),
            )

        print(f"[OK] Created default admin user (username: admin, password: admin123)")

    conn.commit()
    conn.close()

    print(f"[OK] Database initialized at: {resolved_db_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Auth database")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (default: settings.DATABASE_PATH relative to backend/)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("Initializing Auth Backend Database...")
    print("=" * 50 + "\n")

    init_database(args.db_path)

    print("\n" + "=" * 50)
    print("Database initialization complete!")
    print("=" * 50 + "\n")
