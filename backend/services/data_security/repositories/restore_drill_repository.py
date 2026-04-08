from __future__ import annotations

import json
from typing import Any, Callable
from uuid import uuid4

from ..models import RestoreDrill


class RestoreDrillRepository:
    def __init__(self, conn_factory: Callable[[], object]) -> None:
        self._conn_factory = conn_factory

    @staticmethod
    def _from_row(row: Any) -> RestoreDrill:
        report = row["verification_report_json"] if "verification_report_json" in row.keys() else None
        parsed_report = json.loads(report) if report else {}
        return RestoreDrill(
            drill_id=str(row["drill_id"]),
            job_id=int(row["job_id"]),
            backup_path=str(row["backup_path"]),
            backup_hash=str(row["backup_hash"]),
            actual_backup_hash=(str(row["actual_backup_hash"]) if row["actual_backup_hash"] is not None else None),
            hash_match=bool(int(row["hash_match"] or 0)),
            restore_target=str(row["restore_target"]),
            restored_auth_db_path=(
                str(row["restored_auth_db_path"]) if row["restored_auth_db_path"] is not None else None
            ),
            restored_auth_db_hash=(
                str(row["restored_auth_db_hash"]) if row["restored_auth_db_hash"] is not None else None
            ),
            compare_match=bool(int(row["compare_match"] or 0)),
            package_validation_status=(
                str(row["package_validation_status"]) if row["package_validation_status"] is not None else None
            ),
            acceptance_status=(str(row["acceptance_status"]) if row["acceptance_status"] is not None else None),
            executed_by=str(row["executed_by"]),
            executed_at_ms=int(row["executed_at_ms"] or 0),
            result=str(row["result"]),
            verification_notes=row["verification_notes"],
            verification_report=parsed_report,
        )

    def create_restore_drill(
        self,
        *,
        job_id: int,
        backup_path: str,
        backup_hash: str,
        actual_backup_hash: str | None,
        hash_match: bool,
        restore_target: str,
        restored_auth_db_path: str | None,
        restored_auth_db_hash: str | None,
        compare_match: bool,
        package_validation_status: str,
        acceptance_status: str,
        executed_by: str,
        executed_at_ms: int,
        result: str,
        verification_notes: str | None,
        verification_report: dict[str, Any] | None,
    ) -> RestoreDrill:
        normalized_backup_path = str(backup_path or "").strip()
        normalized_backup_hash = str(backup_hash or "").strip()
        normalized_restore_target = str(restore_target or "").strip()
        normalized_executed_by = str(executed_by or "").strip()
        normalized_result = str(result or "").strip().lower()

        if not normalized_backup_path:
            raise ValueError("backup_path_required")
        if not normalized_backup_hash:
            raise ValueError("backup_hash_required")
        if not normalized_restore_target:
            raise ValueError("restore_target_required")
        if not normalized_executed_by:
            raise ValueError("executed_by_required")
        if normalized_result not in ("success", "failed"):
            raise ValueError("invalid_restore_result")
        if package_validation_status not in ("passed", "failed", "blocked"):
            raise ValueError("invalid_package_validation_status")
        if acceptance_status not in ("passed", "failed", "blocked"):
            raise ValueError("invalid_acceptance_status")

        drill_id = f"restore_drill_{uuid4().hex}"
        report_json = json.dumps(verification_report or {}, ensure_ascii=False, sort_keys=True)

        conn = self._conn_factory()
        try:
            conn.execute(
                """
                INSERT INTO restore_drills (
                    drill_id,
                    job_id,
                    backup_path,
                    backup_hash,
                    actual_backup_hash,
                    hash_match,
                    restore_target,
                    restored_auth_db_path,
                    restored_auth_db_hash,
                    compare_match,
                    package_validation_status,
                    acceptance_status,
                    executed_by,
                    executed_at_ms,
                    result,
                    verification_notes,
                    verification_report_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    drill_id,
                    int(job_id),
                    normalized_backup_path,
                    normalized_backup_hash,
                    actual_backup_hash,
                    1 if hash_match else 0,
                    normalized_restore_target,
                    restored_auth_db_path,
                    restored_auth_db_hash,
                    1 if compare_match else 0,
                    package_validation_status,
                    acceptance_status,
                    normalized_executed_by,
                    int(executed_at_ms),
                    normalized_result,
                    verification_notes,
                    report_json,
                ),
            )
            if acceptance_status == "passed":
                conn.execute(
                    """
                    UPDATE backup_jobs
                    SET
                        verified_by = ?,
                        verified_at_ms = ?,
                        verification_status = 'passed',
                        verification_detail = ?,
                        last_restore_drill_id = ?
                    WHERE id = ?
                    """,
                    (
                        normalized_executed_by,
                        int(executed_at_ms),
                        str(verification_notes or ""),
                        drill_id,
                        int(job_id),
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE backup_jobs
                    SET
                        verification_status = ?,
                        verification_detail = ?,
                        last_restore_drill_id = ?
                    WHERE id = ?
                    """,
                    (
                        acceptance_status,
                        str(verification_notes or ""),
                        drill_id,
                        int(job_id),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        conn = self._conn_factory()
        try:
            row = conn.execute("SELECT * FROM restore_drills WHERE drill_id = ?", (drill_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            raise RuntimeError("restore_drill_not_found_after_create")
        return self._from_row(row)

    def list_restore_drills(self, *, limit: int = 30) -> list[RestoreDrill]:
        clamped_limit = int(max(1, min(200, limit)))
        conn = self._conn_factory()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM restore_drills
                ORDER BY executed_at_ms DESC, id DESC
                LIMIT ?
                """,
                (clamped_limit,),
            ).fetchall()
        finally:
            conn.close()
        return [self._from_row(row) for row in rows]
