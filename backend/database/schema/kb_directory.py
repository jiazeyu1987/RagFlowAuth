from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_kb_directory_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "kb_directory_nodes"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_directory_nodes (
                node_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id TEXT,
                created_by TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                FOREIGN KEY(parent_id) REFERENCES kb_directory_nodes(node_id) ON DELETE CASCADE
            )
            """
        )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_directory_nodes_parent_name
        ON kb_directory_nodes(COALESCE(parent_id, ''), name COLLATE NOCASE)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_kb_directory_nodes_parent_id
        ON kb_directory_nodes(parent_id)
        """
    )

    if not table_exists(conn, "kb_directory_dataset_bindings"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_directory_dataset_bindings (
                dataset_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                FOREIGN KEY(node_id) REFERENCES kb_directory_nodes(node_id) ON DELETE CASCADE
            )
            """
        )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_kb_directory_bindings_node_id
        ON kb_directory_dataset_bindings(node_id)
        """
    )
