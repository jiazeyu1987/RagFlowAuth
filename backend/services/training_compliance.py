from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


class TrainingComplianceError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


CONTROLLED_ACTIONS = {"document_review", "restore_drill_execute"}
TRAINING_OUTCOMES = {"passed", "failed"}
EFFECTIVENESS_STATUSES = {"effective", "ineffective", "pending_review"}
CERTIFICATION_STATUSES = {"active", "revoked", "suspended", "expired"}


class TrainingComplianceService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _require_text(value: Any, field_name: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise TrainingComplianceError(f"{field_name}_required", status_code=400)
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _require_known_value(value: Any, *, field_name: str, allowed: set[str]) -> str:
        text = str(value or "").strip().lower()
        if text not in allowed:
            raise TrainingComplianceError(f"invalid_{field_name}", status_code=400)
        return text

    @staticmethod
    def _require_positive_int(value: Any, field_name: str) -> int:
        try:
            number = int(value)
        except Exception as exc:
            raise TrainingComplianceError(f"invalid_{field_name}", status_code=400) from exc
        if number <= 0:
            raise TrainingComplianceError(f"invalid_{field_name}", status_code=400)
        return number

    @staticmethod
    def _require_bool(value: Any, field_name: str) -> int:
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int) and value in (0, 1):
            return value
        raise TrainingComplianceError(f"invalid_{field_name}", status_code=400)

    @staticmethod
    def _serialize_requirement(row) -> dict[str, Any]:
        return {
            "requirement_code": str(row["requirement_code"]),
            "requirement_name": str(row["requirement_name"]),
            "role_code": str(row["role_code"]),
            "controlled_action": str(row["controlled_action"]),
            "curriculum_version": str(row["curriculum_version"]),
            "training_material_ref": str(row["training_material_ref"]),
            "effectiveness_required": bool(int(row["effectiveness_required"] or 0)),
            "recertification_interval_days": int(row["recertification_interval_days"] or 0),
            "review_due_date": (str(row["review_due_date"]) if row["review_due_date"] else None),
            "active": bool(int(row["active"] or 0)),
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    @staticmethod
    def _serialize_training_record(row) -> dict[str, Any]:
        return {
            "record_id": str(row["record_id"]),
            "requirement_code": str(row["requirement_code"]),
            "user_id": str(row["user_id"]),
            "curriculum_version": str(row["curriculum_version"]),
            "trainer_user_id": str(row["trainer_user_id"]),
            "training_outcome": str(row["training_outcome"]),
            "effectiveness_status": str(row["effectiveness_status"]),
            "effectiveness_score": (float(row["effectiveness_score"]) if row["effectiveness_score"] is not None else None),
            "effectiveness_summary": str(row["effectiveness_summary"]),
            "training_notes": (str(row["training_notes"]) if row["training_notes"] else None),
            "completed_at_ms": int(row["completed_at_ms"] or 0),
            "effectiveness_reviewed_by_user_id": (
                str(row["effectiveness_reviewed_by_user_id"]) if row["effectiveness_reviewed_by_user_id"] else None
            ),
            "effectiveness_reviewed_at_ms": (
                int(row["effectiveness_reviewed_at_ms"]) if row["effectiveness_reviewed_at_ms"] is not None else None
            ),
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    @staticmethod
    def _serialize_certification(row) -> dict[str, Any]:
        return {
            "certification_id": str(row["certification_id"]),
            "requirement_code": str(row["requirement_code"]),
            "user_id": str(row["user_id"]),
            "curriculum_version": str(row["curriculum_version"]),
            "certification_status": str(row["certification_status"]),
            "granted_by_user_id": str(row["granted_by_user_id"]),
            "valid_until_ms": int(row["valid_until_ms"] or 0),
            "exception_release_ref": (str(row["exception_release_ref"]) if row["exception_release_ref"] else None),
            "certification_notes": (str(row["certification_notes"]) if row["certification_notes"] else None),
            "granted_at_ms": int(row["granted_at_ms"] or 0),
            "revoked_at_ms": (int(row["revoked_at_ms"]) if row["revoked_at_ms"] is not None else None),
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    def get_requirement(self, requirement_code: str) -> dict[str, Any]:
        requirement_code = self._require_text(requirement_code, "requirement_code")
        conn = self._conn()
        try:
            row = conn.execute(
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
            if row is None:
                raise TrainingComplianceError("training_requirement_not_found", status_code=404)
            return self._serialize_requirement(row)
        finally:
            conn.close()

    def list_requirements(
        self,
        *,
        limit: int = 100,
        controlled_action: str | None = None,
        role_code: str | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        params: list[Any] = []
        conditions: list[str] = []
        if controlled_action:
            conditions.append("controlled_action = ?")
            params.append(str(controlled_action).strip())
        if role_code:
            conditions.append("role_code = ?")
            params.append(str(role_code).strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        conn = self._conn()
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
        return [self.get_requirement(str(row["requirement_code"])) for row in rows]

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
        active: bool,
    ) -> dict[str, Any]:
        requirement_code = self._require_text(requirement_code, "requirement_code")
        requirement_name = self._require_text(requirement_name, "requirement_name")
        role_code = self._require_text(role_code, "role_code")
        controlled_action = self._require_known_value(
            controlled_action,
            field_name="controlled_action",
            allowed=CONTROLLED_ACTIONS,
        )
        curriculum_version = self._require_text(curriculum_version, "curriculum_version")
        training_material_ref = self._require_text(training_material_ref, "training_material_ref")
        effectiveness_required = bool(self._require_bool(effectiveness_required, "effectiveness_required"))
        recertification_interval_days = self._require_positive_int(
            recertification_interval_days,
            "recertification_interval_days",
        )
        review_due_date = self._optional_text(review_due_date)
        active_flag = self._require_bool(active, "active")

        now_ms = int(time.time() * 1000)
        conn = self._conn()
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
        return self.get_requirement(requirement_code)

    def get_training_record(self, record_id: str) -> dict[str, Any]:
        record_id = self._require_text(record_id, "record_id")
        conn = self._conn()
        try:
            row = conn.execute(
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
            if row is None:
                raise TrainingComplianceError("training_record_not_found", status_code=404)
            return self._serialize_training_record(row)
        finally:
            conn.close()

    def list_training_records(
        self,
        *,
        limit: int = 100,
        requirement_code: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        params: list[Any] = []
        conditions: list[str] = []
        if requirement_code:
            conditions.append("requirement_code = ?")
            params.append(str(requirement_code).strip())
        if user_id:
            conditions.append("user_id = ?")
            params.append(str(user_id).strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        conn = self._conn()
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
        return [self.get_training_record(str(row["record_id"])) for row in rows]

    def record_training(
        self,
        *,
        requirement_code: str,
        user_id: str,
        curriculum_version: str,
        trainer_user_id: str,
        training_outcome: str,
        effectiveness_status: str,
        effectiveness_score: float | None,
        effectiveness_summary: str,
        training_notes: str | None,
        completed_at_ms: int | None,
        effectiveness_reviewed_by_user_id: str | None,
        effectiveness_reviewed_at_ms: int | None,
    ) -> dict[str, Any]:
        requirement = self.get_requirement(requirement_code)
        user_id = self._require_text(user_id, "user_id")
        curriculum_version = self._require_text(curriculum_version, "curriculum_version")
        trainer_user_id = self._require_text(trainer_user_id, "trainer_user_id")
        training_outcome = self._require_known_value(
            training_outcome,
            field_name="training_outcome",
            allowed=TRAINING_OUTCOMES,
        )
        effectiveness_status = self._require_known_value(
            effectiveness_status,
            field_name="effectiveness_status",
            allowed=EFFECTIVENESS_STATUSES,
        )
        effectiveness_summary = self._require_text(effectiveness_summary, "effectiveness_summary")
        training_notes = self._optional_text(training_notes)
        reviewed_by_user_id = self._optional_text(effectiveness_reviewed_by_user_id)

        if training_outcome != "passed" and effectiveness_status == "effective":
            raise TrainingComplianceError("training_effectiveness_conflicts_with_outcome", status_code=400)
        if effectiveness_status != "pending_review" and reviewed_by_user_id is None:
            raise TrainingComplianceError("effectiveness_reviewed_by_user_id_required", status_code=400)
        if requirement["active"] is not True:
            raise TrainingComplianceError("training_requirement_inactive", status_code=409)

        when_ms = int(time.time() * 1000) if completed_at_ms is None else int(completed_at_ms)
        reviewed_at_ms = (
            None
            if effectiveness_status == "pending_review"
            else (
                int(effectiveness_reviewed_at_ms)
                if effectiveness_reviewed_at_ms is not None
                else when_ms
            )
        )
        now_ms = int(time.time() * 1000)
        record_id = f"training_record_{uuid4().hex}"
        conn = self._conn()
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
                    requirement["requirement_code"],
                    user_id,
                    curriculum_version,
                    trainer_user_id,
                    training_outcome,
                    effectiveness_status,
                    float(effectiveness_score) if effectiveness_score is not None else None,
                    effectiveness_summary,
                    training_notes,
                    when_ms,
                    reviewed_by_user_id,
                    reviewed_at_ms,
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
        return self.get_training_record(record_id)

    def get_certification(self, certification_id: str) -> dict[str, Any]:
        certification_id = self._require_text(certification_id, "certification_id")
        conn = self._conn()
        try:
            row = conn.execute(
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
            if row is None:
                raise TrainingComplianceError("operator_certification_not_found", status_code=404)
            return self._serialize_certification(row)
        finally:
            conn.close()

    def list_certifications(
        self,
        *,
        limit: int = 100,
        requirement_code: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        params: list[Any] = []
        conditions: list[str] = []
        if requirement_code:
            conditions.append("requirement_code = ?")
            params.append(str(requirement_code).strip())
        if user_id:
            conditions.append("user_id = ?")
            params.append(str(user_id).strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        conn = self._conn()
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
        return [self.get_certification(str(row["certification_id"])) for row in rows]

    def grant_certification(
        self,
        *,
        requirement_code: str,
        user_id: str,
        granted_by_user_id: str,
        certification_status: str = "active",
        valid_until_ms: int | None = None,
        exception_release_ref: str | None = None,
        certification_notes: str | None = None,
        granted_at_ms: int | None = None,
    ) -> dict[str, Any]:
        requirement = self.get_requirement(requirement_code)
        user_id = self._require_text(user_id, "user_id")
        granted_by_user_id = self._require_text(granted_by_user_id, "granted_by_user_id")
        certification_status = self._require_known_value(
            certification_status,
            field_name="certification_status",
            allowed=CERTIFICATION_STATUSES,
        )
        exception_release_ref = self._optional_text(exception_release_ref)
        certification_notes = self._optional_text(certification_notes)
        granted_at_ms = int(time.time() * 1000) if granted_at_ms is None else int(granted_at_ms)
        latest_training = self._latest_training_record(
            requirement_code=requirement["requirement_code"],
            user_id=user_id,
        )
        if latest_training is None:
            raise TrainingComplianceError("training_record_missing", status_code=403)
        if latest_training["curriculum_version"] != requirement["curriculum_version"]:
            raise TrainingComplianceError("training_curriculum_outdated", status_code=403)
        if latest_training["training_outcome"] != "passed":
            raise TrainingComplianceError("training_outcome_not_passed", status_code=403)
        if requirement["effectiveness_required"] and latest_training["effectiveness_status"] != "effective":
            raise TrainingComplianceError("training_effectiveness_not_met", status_code=403)

        if valid_until_ms is None:
            valid_until_ms = granted_at_ms + (
                int(requirement["recertification_interval_days"]) * 24 * 60 * 60 * 1000
            )
        valid_until_ms = int(valid_until_ms)
        if valid_until_ms <= granted_at_ms:
            raise TrainingComplianceError("invalid_valid_until_ms", status_code=400)

        certification_id = f"operator_cert_{uuid4().hex}"
        now_ms = int(time.time() * 1000)
        revoked_at_ms = granted_at_ms if certification_status in {"revoked", "suspended", "expired"} else None
        conn = self._conn()
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
                    requirement["requirement_code"],
                    user_id,
                    requirement["curriculum_version"],
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
        return self.get_certification(certification_id)

    def evaluate_action_status(
        self,
        *,
        user_id: str,
        role_code: str,
        controlled_action: str,
        as_of_ms: int | None = None,
    ) -> dict[str, Any]:
        user_id = self._require_text(user_id, "user_id")
        role_code = self._require_text(role_code, "role_code")
        controlled_action = self._require_known_value(
            controlled_action,
            field_name="controlled_action",
            allowed=CONTROLLED_ACTIONS,
        )
        checked_at_ms = int(time.time() * 1000) if as_of_ms is None else int(as_of_ms)
        requirements = self._requirements_for_action(
            controlled_action=controlled_action,
            role_code=role_code,
        )
        if not requirements:
            raise TrainingComplianceError("training_requirement_not_configured", status_code=409)

        items: list[dict[str, Any]] = []
        allowed = True
        for requirement in requirements:
            latest_training = self._latest_training_record(
                requirement_code=requirement["requirement_code"],
                user_id=user_id,
            )
            latest_certification = self._latest_certification(
                requirement_code=requirement["requirement_code"],
                user_id=user_id,
            )
            item = {
                "requirement_code": requirement["requirement_code"],
                "curriculum_version": requirement["curriculum_version"],
                "training_record_id": (latest_training["record_id"] if latest_training else None),
                "training_outcome": (latest_training["training_outcome"] if latest_training else None),
                "training_curriculum_version": (
                    latest_training["curriculum_version"] if latest_training else None
                ),
                "effectiveness_status": (
                    latest_training["effectiveness_status"] if latest_training else None
                ),
                "certification_id": (
                    latest_certification["certification_id"] if latest_certification else None
                ),
                "certification_status": (
                    latest_certification["certification_status"] if latest_certification else None
                ),
                "certification_valid_until_ms": (
                    latest_certification["valid_until_ms"] if latest_certification else None
                ),
            }
            failure_code = None
            if latest_training is None:
                failure_code = "training_record_missing"
            elif latest_training["curriculum_version"] != requirement["curriculum_version"]:
                failure_code = "training_curriculum_outdated"
            elif latest_training["training_outcome"] != "passed":
                failure_code = "training_outcome_not_passed"
            elif requirement["effectiveness_required"] and latest_training["effectiveness_status"] != "effective":
                failure_code = "training_effectiveness_not_met"
            elif latest_certification is None:
                failure_code = "operator_certification_missing"
            elif latest_certification["curriculum_version"] != requirement["curriculum_version"]:
                failure_code = "operator_certification_outdated"
            elif latest_certification["certification_status"] != "active":
                if latest_certification["certification_status"] == "expired":
                    failure_code = "operator_certification_expired"
                else:
                    failure_code = "operator_certification_inactive"
            elif int(latest_certification["valid_until_ms"]) <= checked_at_ms:
                failure_code = "operator_certification_expired"

            item["allowed"] = failure_code is None
            item["failure_code"] = failure_code
            if failure_code is not None:
                allowed = False
            items.append(item)

        return {
            "user_id": user_id,
            "role_code": role_code,
            "controlled_action": controlled_action,
            "checked_at_ms": checked_at_ms,
            "allowed": allowed,
            "requirements": items,
        }

    def assert_user_authorized_for_action(
        self,
        *,
        user_id: str,
        role_code: str,
        controlled_action: str,
        as_of_ms: int | None = None,
    ) -> dict[str, Any]:
        status = self.evaluate_action_status(
            user_id=user_id,
            role_code=role_code,
            controlled_action=controlled_action,
            as_of_ms=as_of_ms,
        )
        if status["allowed"]:
            return status
        first_failure = next(
            (item["failure_code"] for item in status["requirements"] if item.get("failure_code")),
            "training_requirement_not_met",
        )
        raise TrainingComplianceError(str(first_failure), status_code=403)

    def _requirements_for_action(self, *, controlled_action: str, role_code: str) -> list[dict[str, Any]]:
        conn = self._conn()
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
        return [self.get_requirement(str(row["requirement_code"])) for row in rows]

    def _latest_training_record(self, *, requirement_code: str, user_id: str) -> dict[str, Any] | None:
        conn = self._conn()
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
        return self.get_training_record(str(row["record_id"]))

    def _latest_certification(self, *, requirement_code: str, user_id: str) -> dict[str, Any] | None:
        conn = self._conn()
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
        return self.get_certification(str(row["certification_id"]))
