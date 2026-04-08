from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .training_compliance_repository import TrainingComplianceRepository
from .training_compliance_support import (
    CERTIFICATION_STATUSES,
    CONTROLLED_ACTIONS,
    EFFECTIVENESS_STATUSES,
    TRAINING_OUTCOMES,
    TrainingComplianceError,
    optional_text,
    require_bool,
    require_known_value,
    require_positive_int,
    require_text,
    serialize_certification,
    serialize_requirement,
    serialize_training_record,
)


class TrainingComplianceService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.repository = TrainingComplianceRepository(self._conn)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def get_requirement(self, requirement_code: str) -> dict[str, Any]:
        normalized_code = require_text(requirement_code, "requirement_code")
        row = self.repository.get_requirement_row(normalized_code)
        if row is None:
            raise TrainingComplianceError("training_requirement_not_found", status_code=404)
        return serialize_requirement(row)

    def list_requirements(
        self,
        *,
        limit: int = 100,
        controlled_action: str | None = None,
        role_code: str | None = None,
    ) -> list[dict[str, Any]]:
        clamped_limit = max(1, min(int(limit or 100), 200))
        codes = self.repository.list_requirement_codes(
            limit=clamped_limit,
            controlled_action=controlled_action,
            role_code=role_code,
        )
        return [self.get_requirement(code) for code in codes]

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
        normalized_code = require_text(requirement_code, "requirement_code")
        normalized_name = require_text(requirement_name, "requirement_name")
        normalized_role_code = require_text(role_code, "role_code")
        normalized_action = require_known_value(
            controlled_action,
            field_name="controlled_action",
            allowed=CONTROLLED_ACTIONS,
        )
        normalized_curriculum = require_text(curriculum_version, "curriculum_version")
        normalized_material_ref = require_text(
            training_material_ref,
            "training_material_ref",
        )
        normalized_effectiveness_required = bool(
            require_bool(effectiveness_required, "effectiveness_required")
        )
        normalized_recertification_days = require_positive_int(
            recertification_interval_days,
            "recertification_interval_days",
        )
        normalized_review_due_date = optional_text(review_due_date)
        active_flag = require_bool(active, "active")

        self.repository.upsert_requirement(
            requirement_code=normalized_code,
            requirement_name=normalized_name,
            role_code=normalized_role_code,
            controlled_action=normalized_action,
            curriculum_version=normalized_curriculum,
            training_material_ref=normalized_material_ref,
            effectiveness_required=normalized_effectiveness_required,
            recertification_interval_days=normalized_recertification_days,
            review_due_date=normalized_review_due_date,
            active_flag=active_flag,
            now_ms=int(time.time() * 1000),
        )
        return self.get_requirement(normalized_code)

    def get_training_record(self, record_id: str) -> dict[str, Any]:
        normalized_record_id = require_text(record_id, "record_id")
        row = self.repository.get_training_record_row(normalized_record_id)
        if row is None:
            raise TrainingComplianceError("training_record_not_found", status_code=404)
        return serialize_training_record(row)

    def list_training_records(
        self,
        *,
        limit: int = 100,
        requirement_code: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clamped_limit = max(1, min(int(limit or 100), 200))
        record_ids = self.repository.list_training_record_ids(
            limit=clamped_limit,
            requirement_code=requirement_code,
            user_id=user_id,
        )
        return [self.get_training_record(record_id) for record_id in record_ids]

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
        normalized_user_id = require_text(user_id, "user_id")
        normalized_curriculum = require_text(curriculum_version, "curriculum_version")
        normalized_trainer_user_id = require_text(trainer_user_id, "trainer_user_id")
        normalized_training_outcome = require_known_value(
            training_outcome,
            field_name="training_outcome",
            allowed=TRAINING_OUTCOMES,
        )
        normalized_effectiveness_status = require_known_value(
            effectiveness_status,
            field_name="effectiveness_status",
            allowed=EFFECTIVENESS_STATUSES,
        )
        normalized_effectiveness_summary = require_text(
            effectiveness_summary,
            "effectiveness_summary",
        )
        normalized_training_notes = optional_text(training_notes)
        reviewed_by_user_id = optional_text(effectiveness_reviewed_by_user_id)

        if (
            normalized_training_outcome != "passed"
            and normalized_effectiveness_status == "effective"
        ):
            raise TrainingComplianceError(
                "training_effectiveness_conflicts_with_outcome",
                status_code=400,
            )
        if (
            normalized_effectiveness_status != "pending_review"
            and reviewed_by_user_id is None
        ):
            raise TrainingComplianceError(
                "effectiveness_reviewed_by_user_id_required",
                status_code=400,
            )
        if requirement["active"] is not True:
            raise TrainingComplianceError("training_requirement_inactive", status_code=409)

        when_ms = int(time.time() * 1000) if completed_at_ms is None else int(completed_at_ms)
        reviewed_at_ms = (
            None
            if normalized_effectiveness_status == "pending_review"
            else (
                int(effectiveness_reviewed_at_ms)
                if effectiveness_reviewed_at_ms is not None
                else when_ms
            )
        )
        record_id = f"training_record_{uuid4().hex}"
        now_ms = int(time.time() * 1000)

        self.repository.insert_training_record(
            record_id=record_id,
            requirement_code=requirement["requirement_code"],
            user_id=normalized_user_id,
            curriculum_version=normalized_curriculum,
            trainer_user_id=normalized_trainer_user_id,
            training_outcome=normalized_training_outcome,
            effectiveness_status=normalized_effectiveness_status,
            effectiveness_score=effectiveness_score,
            effectiveness_summary=normalized_effectiveness_summary,
            training_notes=normalized_training_notes,
            completed_at_ms=when_ms,
            effectiveness_reviewed_by_user_id=reviewed_by_user_id,
            effectiveness_reviewed_at_ms=reviewed_at_ms,
            now_ms=now_ms,
        )
        return self.get_training_record(record_id)

    def get_certification(self, certification_id: str) -> dict[str, Any]:
        normalized_certification_id = require_text(certification_id, "certification_id")
        row = self.repository.get_certification_row(normalized_certification_id)
        if row is None:
            raise TrainingComplianceError(
                "operator_certification_not_found",
                status_code=404,
            )
        return serialize_certification(row)

    def list_certifications(
        self,
        *,
        limit: int = 100,
        requirement_code: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clamped_limit = max(1, min(int(limit or 100), 200))
        certification_ids = self.repository.list_certification_ids(
            limit=clamped_limit,
            requirement_code=requirement_code,
            user_id=user_id,
        )
        return [self.get_certification(certification_id) for certification_id in certification_ids]

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
        normalized_user_id = require_text(user_id, "user_id")
        normalized_granted_by_user_id = require_text(
            granted_by_user_id,
            "granted_by_user_id",
        )
        normalized_status = require_known_value(
            certification_status,
            field_name="certification_status",
            allowed=CERTIFICATION_STATUSES,
        )
        normalized_exception_release_ref = optional_text(exception_release_ref)
        normalized_certification_notes = optional_text(certification_notes)
        granted_ms = int(time.time() * 1000) if granted_at_ms is None else int(granted_at_ms)

        latest_training = self._latest_training_record(
            requirement_code=requirement["requirement_code"],
            user_id=normalized_user_id,
        )
        if latest_training is None:
            raise TrainingComplianceError("training_record_missing", status_code=403)
        if latest_training["curriculum_version"] != requirement["curriculum_version"]:
            raise TrainingComplianceError("training_curriculum_outdated", status_code=403)
        if latest_training["training_outcome"] != "passed":
            raise TrainingComplianceError("training_outcome_not_passed", status_code=403)
        if (
            requirement["effectiveness_required"]
            and latest_training["effectiveness_status"] != "effective"
        ):
            raise TrainingComplianceError("training_effectiveness_not_met", status_code=403)

        resolved_valid_until_ms = valid_until_ms
        if resolved_valid_until_ms is None:
            resolved_valid_until_ms = granted_ms + (
                int(requirement["recertification_interval_days"]) * 24 * 60 * 60 * 1000
            )
        resolved_valid_until_ms = int(resolved_valid_until_ms)
        if resolved_valid_until_ms <= granted_ms:
            raise TrainingComplianceError("invalid_valid_until_ms", status_code=400)

        certification_id = f"operator_cert_{uuid4().hex}"
        revoked_at_ms = (
            granted_ms
            if normalized_status in {"revoked", "suspended", "expired"}
            else None
        )
        now_ms = int(time.time() * 1000)

        self.repository.insert_certification(
            certification_id=certification_id,
            requirement_code=requirement["requirement_code"],
            user_id=normalized_user_id,
            curriculum_version=requirement["curriculum_version"],
            certification_status=normalized_status,
            granted_by_user_id=normalized_granted_by_user_id,
            valid_until_ms=resolved_valid_until_ms,
            exception_release_ref=normalized_exception_release_ref,
            certification_notes=normalized_certification_notes,
            granted_at_ms=granted_ms,
            revoked_at_ms=revoked_at_ms,
            now_ms=now_ms,
        )
        return self.get_certification(certification_id)

    def evaluate_action_status(
        self,
        *,
        user_id: str,
        role_code: str,
        controlled_action: str,
        as_of_ms: int | None = None,
    ) -> dict[str, Any]:
        normalized_user_id = require_text(user_id, "user_id")
        normalized_role_code = require_text(role_code, "role_code")
        normalized_action = require_known_value(
            controlled_action,
            field_name="controlled_action",
            allowed=CONTROLLED_ACTIONS,
        )
        checked_at_ms = int(time.time() * 1000) if as_of_ms is None else int(as_of_ms)
        requirements = self._requirements_for_action(
            controlled_action=normalized_action,
            role_code=normalized_role_code,
        )
        if not requirements:
            raise TrainingComplianceError("training_requirement_not_configured", status_code=409)

        items: list[dict[str, Any]] = []
        allowed = True
        for requirement in requirements:
            latest_training = self._latest_training_record(
                requirement_code=requirement["requirement_code"],
                user_id=normalized_user_id,
            )
            latest_certification = self._latest_certification(
                requirement_code=requirement["requirement_code"],
                user_id=normalized_user_id,
            )
            item = {
                "requirement_code": requirement["requirement_code"],
                "curriculum_version": requirement["curriculum_version"],
                "training_record_id": (
                    latest_training["record_id"] if latest_training else None
                ),
                "training_outcome": (
                    latest_training["training_outcome"] if latest_training else None
                ),
                "training_curriculum_version": (
                    latest_training["curriculum_version"] if latest_training else None
                ),
                "effectiveness_status": (
                    latest_training["effectiveness_status"] if latest_training else None
                ),
                "certification_id": (
                    latest_certification["certification_id"]
                    if latest_certification
                    else None
                ),
                "certification_status": (
                    latest_certification["certification_status"]
                    if latest_certification
                    else None
                ),
                "certification_valid_until_ms": (
                    latest_certification["valid_until_ms"]
                    if latest_certification
                    else None
                ),
            }

            failure_code = None
            if latest_training is None:
                failure_code = "training_record_missing"
            elif latest_training["curriculum_version"] != requirement["curriculum_version"]:
                failure_code = "training_curriculum_outdated"
            elif latest_training["training_outcome"] != "passed":
                failure_code = "training_outcome_not_passed"
            elif (
                requirement["effectiveness_required"]
                and latest_training["effectiveness_status"] != "effective"
            ):
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
            "user_id": normalized_user_id,
            "role_code": normalized_role_code,
            "controlled_action": normalized_action,
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
            (
                item["failure_code"]
                for item in status["requirements"]
                if item.get("failure_code")
            ),
            "training_requirement_not_met",
        )
        raise TrainingComplianceError(str(first_failure), status_code=403)

    def _requirements_for_action(
        self,
        *,
        controlled_action: str,
        role_code: str,
    ) -> list[dict[str, Any]]:
        requirement_codes = self.repository.list_requirement_codes_for_action(
            controlled_action=controlled_action,
            role_code=role_code,
        )
        return [self.get_requirement(requirement_code) for requirement_code in requirement_codes]

    def _latest_training_record(
        self,
        *,
        requirement_code: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        record_id = self.repository.latest_training_record_id(
            requirement_code=requirement_code,
            user_id=user_id,
        )
        if record_id is None:
            return None
        return self.get_training_record(record_id)

    def _latest_certification(
        self,
        *,
        requirement_code: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        certification_id = self.repository.latest_certification_id(
            requirement_code=requirement_code,
            user_id=user_id,
        )
        if certification_id is None:
            return None
        return self.get_certification(certification_id)
