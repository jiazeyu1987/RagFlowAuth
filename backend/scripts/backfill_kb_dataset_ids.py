from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from backend.database.paths import resolve_auth_db_path

from backend.database.sqlite import connect_sqlite
from backend.runtime.runner import ensure_database
from backend.services.ragflow_connection import create_ragflow_connection
from backend.services.ragflow_service import RagflowService


def _resolve_db_path(raw: str | None) -> Path:
    return resolve_auth_db_path(raw)


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


def _backfill_table(
    conn: sqlite3.Connection,
    table_name: str,
    *,
    id_column: str | None,
    dataset_index: dict,
) -> int:
    cols = _columns(conn, table_name)
    if "kb_id" not in cols or "kb_dataset_id" not in cols or "kb_name" not in cols:
        return 0

    by_name = (dataset_index or {}).get("by_name", {})
    by_id = (dataset_index or {}).get("by_id", {})

    rows = conn.execute(
        f"SELECT {id_column + ',' if id_column else ''} kb_id, kb_dataset_id, kb_name FROM {table_name}"
    ).fetchall()

    updated = 0
    for row in rows:
        if id_column:
            row_id = row[0]
            kb_id = row[1]
            kb_dataset_id = row[2]
            kb_name = row[3]
        else:
            row_id = None
            kb_id = row[0]
            kb_dataset_id = row[1]
            kb_name = row[2]

        if kb_dataset_id:
            continue
        if not isinstance(kb_id, str) or not kb_id:
            continue

        # kb_id might already be a dataset_id (if we canonicalized earlier)
        dataset_id = kb_id if kb_id in by_id else by_name.get(kb_id)
        if not dataset_id:
            continue

        name = by_id.get(dataset_id) or kb_name or kb_id

        if id_column:
            conn.execute(
                f"UPDATE {table_name} SET kb_dataset_id = ?, kb_name = ? WHERE {id_column} = ?",
                (dataset_id, name, row_id),
            )
        else:
            conn.execute(
                f"UPDATE {table_name} SET kb_dataset_id = ?, kb_name = ? WHERE kb_id = ? AND (kb_dataset_id IS NULL OR kb_dataset_id = '')",
                (dataset_id, name, kb_id),
            )
        updated += 1

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill kb_dataset_id/kb_name based on RAGFlow datasets")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to auth.db (relative paths are resolved from repo root)",
    )
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db_path)
    ensure_database(db_path=db_path)
    conn = connect_sqlite(db_path)
    try:
        ragflow_conn = create_ragflow_connection()
        ragflow = RagflowService(connection=ragflow_conn)
        index = ragflow.get_dataset_index()

        if not _table_exists(conn, "kb_documents"):
            print("[SKIP] kb_documents not found")
        else:
            updated = _backfill_table(conn, "kb_documents", id_column=None, dataset_index=index)
            print(f"[OK] kb_documents updated: {updated}")

        if not _table_exists(conn, "download_logs"):
            print("[SKIP] download_logs not found")
        else:
            updated = _backfill_table(conn, "download_logs", id_column="id", dataset_index=index)
            print(f"[OK] download_logs updated: {updated}")

        if not _table_exists(conn, "deletion_logs"):
            print("[SKIP] deletion_logs not found")
        else:
            updated = _backfill_table(conn, "deletion_logs", id_column="id", dataset_index=index)
            print(f"[OK] deletion_logs updated: {updated}")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
