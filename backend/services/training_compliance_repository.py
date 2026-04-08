from __future__ import annotations

from typing import Any, Callable


class TrainingComplianceRepository:
    def __init__(self, conn_factory: Callable[[], Any]) -> None:
        self._conn_factory = conn_factory

    def get_requirement_row(self, requirement_code: str):
        conn = self._conn_factory()
        try:
            return conn.execute(
                """
                SELECT
                    requirement_code,
                    requirement_name,
                    role_code,
                    controlled_action,
                    curriculum_version,
                    training_material_ref,
                    effectiveness_required,
                    recertification_interval_days,
                    review_due_date,
                    active,
                    created_at_ms,
                    updated_at_ms
                FROM training_requirements
                WHERE requirement_code = ?
                """,
                (requirement_code,),
            ).fetchone()
        finally:
            conn.close()

    def list_requirement_codes(
        self,
        *,
        limit: int,
        controlled_action: str | None = None,
        role_code: str | None = None,
    ) -> list[str]:
        params: list[Any] = []
        conditions: list[str] = []
        if controlled_action:
            conditions.append("controlled_action = ?")
            params.append(str(controlled_action).strip())
        if role_code:
            conditions.append("role_code = ?")
            params.append(str(role_code).strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        conn = self._conn_factory()
        try:
            rows = conn.execute(
                f"""
                SELECT requirement_code
                FROM training_requirements
                {where}
                ORDER BY controlled_action ASC, role_code ASC, requirement_code ASC
                LIMIT ?
                """,
                tuple(params + [limit]),
            ).fetchall()
        finally:
            conn.close()
        return [str(row["requirement_code"]) for row in rows]

    def upsert_requirement(
        self,
        *,
        requirement_code: str,
        requirement_name: str,
        role_code: str,
        controlled_action: str,
        curriculum_version: str,
        training_material_ref: str,
        effectiveness_required: bool,
        recertification_interval_days: int,
        review_due_date: str | None,
        active_flag: int,
        now_ms: int,
    ) -> str:
        conn = self._conn_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT requirement_code FROM training_requirements WHERE requirement_code = ?",
                (requirement_code,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO training_requirements (
                        requirement_code,
                        requirement_name,
                        role_code,
                        controlled_action,
                        curriculum_version,
                        training_material_ref,
                        effectiveness_required,
                        recertification_interval_days,
                        review_due_date,
                        active,
                        created_at_ms,
                        updated_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        requirement_code,
                        requirement_name,
                        role_code,
                        controlled_action,
                        curriculum_version,
                        training_material_ref,
                        1 if effectiveness_required else 0,
                        recertification_interval_days,
                        review_due_date,
                        active_flag,
                        now_ms,
                        now_ms,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE training_requirements
                    SET requirement_name = ?,
                        role_code = ?,
                        controlled_action = ?,
                        curriculum_version = ?,
                        training_material_ref = ?,
                        effectiveness_required = ?,
                        recertification_interval_days = ?,
                        review_due_date = ?,
                        active = ?,
                        updated_at_ms = ?
                    WHERE requirement_code = ?
                    """,
                    (
                        requirement_name,
                        role_code,
                        controlled_action,
                        curriculum_version,
                        training_material_ref,
                        1 if effectiveness_required else 0,
                        recertification_interval_days,
                        review_due_date,
                        active_flag,
                        now_ms,
                        requirement_code,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return requirement_code

    def get_training_record_row(self, record_id: str):
        conn = self._conn_factory()
        try:
            return conn.execute(
                """
                SELECT
                    record_id,
                    requirement_code,
                    user_id,
                    curriculum_version,
                    trainer_user_id,
                    training_outcome,
                    effectiveness_status,
                    effectiveness_score,
                    effectiveness_summary,
                    training_notes,
                    completed_at_ms,
                    effectiveness_reviewed_by_user_id,
                    effectiveness_reviewed_at_ms,
                    created_at_ms,
                    updated_at_ms
                FROM training_records
                WHERE record_id = ?
                """,
                (record_id,),
            ).fetchone()
        finally:
            conn.close()

    def list_training_record_ids(
        self,
        *,
        limit: int,
        requirement_code: str | None = None,
        user_id: str | None = None,
    ) -> list[str]:
        params: list[Any] = []
        conditions: list[str] = []
        if requirement_code:
            conditions.append("requirement_code = ?")
            params.append(str(requirement_code).strip())
        if user_id:
            conditions.append("user_id = ?")
            params.append(str(user_id).strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        conn = self._conn_factory()
        try:
            rows = conn.execute(
                f"""
                SELECT record_id
                FROM training_records
                {where}
                ORDER BY completed_at_ms DESC, record_id DESC
                LIMIT ?
                """,
                tuple(params + [limit]),
            ).fetchall()
        finally:
            conn.close()
        return [str(row["record_id"]) for row in rows]

    def insert_training_record(
        self,
        *,
        record_id: str,
        requirement_code: str,
        user_id: str,
        curriculum_version: str,
        trainer_user_id: str,
        training_outcome: str,
        effectiveness_status: str,
        effectiveness_score: float | None,
        effectiveness_summary: str,
        training_notes: str | None,
        completed_at_ms: int,
        effectiveness_reviewed_by_user_id: str | None,
        effectiveness_reviewed_at_ms: int | None,
        now_ms: int,
    ) -> str:
        conn = self._conn_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO training_records (
                    record_id,
                    requirement_code,
                    user_id,
                    curriculum_version,
                    trainer_user_id,
                    training_outcome,
                    effectiveness_status,
                    effectiveness_score,
                    effectiveness_summary,
                    training_notes,
                    completed_at_ms,
                    effectiveness_reviewed_by_user_id,
                    effectiveness_reviewed_at_ms,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    requirement_code,
                    user_id,
                    curriculum_version,
                    trainer_user_id,
                    training_outcome,
                    effectiveness_status,
                    float(effectiveness_score) if effectiveness_score is not None else None,
                    effectiveness_summary,
                    training_notes,
                    completed_at_ms,
                    effectiveness_reviewed_by_user_id,
                    effectiveness_reviewed_at_ms,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return record_id

    def get_certification_row(self, certification_id: str):
        conn = self._conn_factory()
        try:
            return conn.execute(
                """
                SELECT
                    certification_id,
                    requirement_code,
                    user_id,
                    curriculum_version,
                    certification_status,
                    granted_by_user_id,
                    valid_until_ms,
                    exception_release_ref,
                    certification_notes,
                    granted_at_ms,
                    revoked_at_ms,
                    created_at_ms,
                    updated_at_ms
                FROM operator_certifications
                WHERE certification_id = ?
                """,
                (certification_id,),
            ).fetchone()
        finally:
            conn.close()

    def list_certification_ids(
        self,
        *,
        limit: int,
        requirement_code: str | None = None,
        user_id: str | None = None,
    ) -> list[str]:
        params: list[Any] = []
        conditions: list[str] = []
        if requirement_code:
            conditions.append("requirement_code = ?")
            params.append(str(requirement_code).strip())
        if user_id:
            conditions.append("user_id = ?")
            params.append(str(user_id).strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        conn = self._conn_factory()
        try:
            rows = conn.execute(
                f"""
                SELECT certification_id
                FROM operator_certifications
                {where}
                ORDER BY granted_at_ms DESC, certification_id DESC
                LIMIT ?
                """,
                tuple(params + [limit]),
            ).fetchall()
        finally:
            conn.close()
        return [str(row["certification_id"]) for row in rows]

    def insert_certification(
        self,
        *,
        certification_id: str,
        requirement_code: str,
        user_id: str,
        curriculum_version: str,
        certification_status: str,
        granted_by_user_id: str,
        valid_until_ms: int,
        exception_release_ref: str | None,
        certification_notes: str | None,
        granted_at_ms: int,
        revoked_at_ms: int | None,
        now_ms: int,
    ) -> str:
        conn = self._conn_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO operator_certifications (
                    certification_id,
                    requirement_code,
                    user_id,
                    curriculum_version,
                    certification_status,
                    granted_by_user_id,
                    valid_until_ms,
                    exception_release_ref,
                    certification_notes,
                    granted_at_ms,
                    revoked_at_ms,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    certification_id,
                    requirement_code,
                    user_id,
                    curriculum_version,
                    certification_status,
                    granted_by_user_id,
                    valid_until_ms,
                    exception_release_ref,
                    certification_notes,
                    granted_at_ms,
                    revoked_at_ms,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return certification_id

    def list_requirement_codes_for_action(
        self,
        *,
        controlled_action: str,
        role_code: str,
    ) -> list[str]:
        conn = self._conn_factory()
        try:
            rows = conn.execute(
                """
                SELECT requirement_code
                FROM training_requirements
                WHERE active = 1
                  AND controlled_action = ?
                  AND role_code IN (?, '*')
                ORDER BY requirement_code ASC
                """,
                (controlled_action, role_code),
            ).fetchall()
        finally:
            conn.close()
        return [str(row["requirement_code"]) for row in rows]

    def latest_training_record_id(self, *, requirement_code: str, user_id: str) -> str | None:
        conn = self._conn_factory()
        try:
            row = conn.execute(
                """
                SELECT record_id
                FROM training_records
                WHERE requirement_code = ?
                  AND user_id = ?
                ORDER BY completed_at_ms DESC, record_id DESC
                LIMIT 1
                """,
                (requirement_code, user_id),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return str(row["record_id"])

    def latest_certification_id(self, *, requirement_code: str, user_id: str) -> str | None:
        conn = self._conn_factory()
        try:
            row = conn.execute(
                """
                SELECT certification_id
                FROM operator_certifications
                WHERE requirement_code = ?
                  AND user_id = ?
                ORDER BY granted_at_ms DESC, certification_id DESC
                LIMIT 1
                """,
                (requirement_code, user_id),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return str(row["certification_id"])
