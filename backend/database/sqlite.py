from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


def connect_sqlite(
    db_path: str | Path,
    *,
    timeout_s: float = 30.0,
    row_factory: Any = sqlite3.Row,
    pragmas: Iterable[str] | None = None,
) -> sqlite3.Connection:
    """
    Create a sqlite3 connection with consistent defaults across the project.

    - row_factory defaults to sqlite3.Row (supports both index and name access).
    - pragmas are applied best-effort (ignored on unsupported/read-only setups).
    """
    conn = sqlite3.connect(str(db_path), timeout=timeout_s)
    conn.row_factory = row_factory

    if pragmas is None:
        pragmas = (
            "PRAGMA foreign_keys = ON",
            "PRAGMA busy_timeout = 5000",
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
        )

    for stmt in pragmas:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            continue

    return conn

