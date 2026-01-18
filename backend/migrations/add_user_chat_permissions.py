"""
Migration wrapper: ensure user_chat_permissions table exists.

Run:
    python -m backend.migrations.add_user_chat_permissions

Note:
    The canonical schema is managed by database.schema_migrations.ensure_schema().
    This script remains for backward compatibility with older operations.
"""

from __future__ import annotations

from backend.database.paths import resolve_auth_db_path
from backend.database.schema_migrations import ensure_schema


def migrate(db_path: str | None = None) -> bool:
    resolved = resolve_auth_db_path(db_path)
    if not resolved.exists():
        print(f"[ERROR] Database not found: {resolved}")
        return False

    print(f"[INFO] Ensuring schema: {resolved}")
    ensure_schema(str(resolved))
    print("[OK] Schema ensured (includes user_chat_permissions)")
    return True


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ensure user_chat_permissions table exists")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (default: settings.DATABASE_PATH relative to backend/)",
    )
    args = parser.parse_args()

    ok = migrate(args.db_path)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
