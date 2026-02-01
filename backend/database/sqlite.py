from __future__ import annotations

import sqlite3
import time
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
    # On some deployments (especially with bind mounts) sqlite may transiently fail to open the DB file
    # (e.g. during backup/restore operations or brief IO hiccups). Add a small retry window to avoid
    # leaking sporadic 500s to callers.
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            conn = sqlite3.connect(str(db_path), timeout=timeout_s)
            break
        except sqlite3.OperationalError as e:
            last_err = e
            msg = str(e).lower()
            if "unable to open database file" not in msg and "database is locked" not in msg:
                raise
            # 0.1s, 0.2s, 0.4s, 0.8s, 1.6s (max ~3.1s total)
            time.sleep(0.1 * (2**attempt))
    else:
        assert last_err is not None
        raise last_err
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
