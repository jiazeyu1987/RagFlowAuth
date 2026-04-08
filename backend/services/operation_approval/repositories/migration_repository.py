from __future__ import annotations

import time

from ._base import OperationApprovalRepositoryBase


class OperationApprovalMigrationRepository(OperationApprovalRepositoryBase):
    def get_legacy_migration(self, *, legacy_instance_id: str) -> dict | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT legacy_instance_id, request_id, company_id, source_db_path, status, error, migrated_at_ms
                FROM operation_approval_legacy_migrations
                WHERE legacy_instance_id = ?
                """,
                (legacy_instance_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "legacy_instance_id": str(row["legacy_instance_id"]),
                "request_id": (str(row["request_id"]) if row["request_id"] else None),
                "company_id": (int(row["company_id"]) if row["company_id"] is not None else None),
                "source_db_path": (str(row["source_db_path"]) if row["source_db_path"] else None),
                "status": str(row["status"]),
                "error": (str(row["error"]) if row["error"] else None),
                "migrated_at_ms": int(row["migrated_at_ms"] or 0),
            }
        finally:
            conn.close()

    def record_legacy_migration(
        self,
        *,
        legacy_instance_id: str,
        request_id: str | None,
        company_id: int | None,
        source_db_path: str | None,
        status: str,
        error: str | None,
    ) -> dict:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO operation_approval_legacy_migrations (
                    legacy_instance_id, request_id, company_id, source_db_path, status, error, migrated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(legacy_instance_id) DO UPDATE SET
                    request_id = excluded.request_id,
                    company_id = excluded.company_id,
                    source_db_path = excluded.source_db_path,
                    status = excluded.status,
                    error = excluded.error,
                    migrated_at_ms = excluded.migrated_at_ms
                """,
                (
                    legacy_instance_id,
                    request_id,
                    company_id,
                    source_db_path,
                    status,
                    error,
                    now_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        item = self.get_legacy_migration(legacy_instance_id=legacy_instance_id)
        if not item:
            raise RuntimeError("operation_approval_legacy_migration_record_failed")
        return item
