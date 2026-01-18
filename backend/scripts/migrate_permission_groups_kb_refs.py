from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from backend.database.paths import resolve_auth_db_path

from backend.database.schema_migrations import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.ragflow_connection import create_ragflow_connection
from backend.services.ragflow_service import RagflowService


def _resolve_db_path(raw: str | None) -> Path:
    return resolve_auth_db_path(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize permission_groups.accessible_kbs to dataset_id when possible")
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
        cur = conn.execute(
            "SELECT group_id, group_name, accessible_kbs FROM permission_groups ORDER BY group_id"
        )
        rows = cur.fetchall()
        if not rows:
            print("[OK] No permission_groups rows")
            return

        ragflow_conn = create_ragflow_connection()
        ragflow = RagflowService(connection=ragflow_conn)
        index = ragflow.get_dataset_index()
        by_id = index.get("by_id", {})
        by_name = index.get("by_name", {})

        changed = 0
        for row in rows:
            raw = row["accessible_kbs"] or "[]"
            try:
                items = json.loads(raw)
            except Exception:
                items = []
            if not isinstance(items, list):
                items = []

            normalized: list[str] = []
            for ref in items:
                if not isinstance(ref, str) or not ref:
                    continue
                dataset_id = ref if ref in by_id else by_name.get(ref)
                normalized.append(dataset_id or ref)

            # de-dupe preserving order
            seen: set[str] = set()
            deduped: list[str] = []
            for ref in normalized:
                if ref in seen:
                    continue
                seen.add(ref)
                deduped.append(ref)

            new_json = json.dumps(deduped, ensure_ascii=False)
            if new_json == (raw if isinstance(raw, str) else str(raw)):
                continue

            changed += 1
            print(
                f"[CHANGE] group_id={row['group_id']} group_name={row['group_name']} accessible_kbs: {raw} -> {new_json}"
            )
            if not args.dry_run:
                conn.execute(
                    "UPDATE permission_groups SET accessible_kbs = ? WHERE group_id = ?",
                    (new_json, row["group_id"]),
                )

        if not args.dry_run:
            conn.commit()
        print(f"[OK] Groups changed: {changed} (dry_run={args.dry_run})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
