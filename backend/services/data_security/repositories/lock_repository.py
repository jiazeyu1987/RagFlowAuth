from __future__ import annotations

import time
from typing import Callable


class BackupLockRepository:
    def __init__(self, conn_factory: Callable[[], object], *, lock_owner: str) -> None:
        self._conn_factory = conn_factory
        self._lock_owner = str(lock_owner)

    @staticmethod
    def _normalize_name(name: str | None) -> str:
        return str(name or "").strip() or "backup"

    def acquire_lock(self, *, name: str, job_id: int | None, ttl_ms: int) -> bool:
        """
        Acquire a cross-process lock stored in sqlite.

        Uses `BEGIN IMMEDIATE` to ensure the check-and-set is atomic across
        processes. If the lock exists but is older than `ttl_ms`, it is taken over.
        """
        lock_name = self._normalize_name(name)
        now_ms = int(time.time() * 1000)
        ttl_ms = int(max(1, ttl_ms))

        conn = self._conn_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT owner, acquired_at_ms FROM backup_locks WHERE name = ?",
                (lock_name,),
            ).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO backup_locks (name, owner, job_id, acquired_at_ms) VALUES (?, ?, ?, ?)",
                    (lock_name, self._lock_owner, job_id, now_ms),
                )
                conn.commit()
                return True

            acquired_at_ms = int(row["acquired_at_ms"] or 0)
            if now_ms - acquired_at_ms > ttl_ms:
                conn.execute(
                    "UPDATE backup_locks SET owner = ?, job_id = ?, acquired_at_ms = ? WHERE name = ?",
                    (self._lock_owner, job_id, now_ms, lock_name),
                )
                conn.commit()
                return True

            conn.rollback()
            return False
        finally:
            conn.close()

    def release_lock(self, *, name: str, job_id: int | None = None, force: bool = False) -> bool:
        lock_name = self._normalize_name(name)
        conn = self._conn_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if force:
                cur = conn.execute("DELETE FROM backup_locks WHERE name = ?", (lock_name,))
            elif job_id is not None:
                cur = conn.execute(
                    """
                    DELETE FROM backup_locks
                    WHERE name = ?
                      AND (owner = ? OR job_id = ?)
                    """,
                    (lock_name, self._lock_owner, int(job_id)),
                )
            else:
                cur = conn.execute(
                    "DELETE FROM backup_locks WHERE name = ? AND owner = ?",
                    (lock_name, self._lock_owner),
                )
            conn.commit()
            return bool(cur.rowcount)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()
