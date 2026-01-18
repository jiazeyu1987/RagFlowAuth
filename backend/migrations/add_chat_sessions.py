"""
Migration wrapper: ensure chat_sessions table exists.

Run:
    python -m backend.migrations.add_chat_sessions

Note:
    The canonical schema is managed by database.schema_migrations.ensure_schema().
    This script remains for backward compatibility with older operations.
"""

from __future__ import annotations

from backend.database.paths import resolve_auth_db_path
from backend.runtime.runner import ensure_database


def migrate(db_path: str | None = None) -> bool:
    resolved = resolve_auth_db_path(db_path)
    if not resolved.exists():
        print(f"[ERROR] Database not found: {resolved}")
        return False

    print(f"[INFO] Ensuring schema: {resolved}")
    ensure_database(db_path=resolved)
    print("[OK] Schema ensured (includes chat_sessions)")
    return True


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ensure chat_sessions table exists")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (relative paths are resolved from repo root)",
    )
    args = parser.parse_args()

    ok = migrate(args.db_path)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
