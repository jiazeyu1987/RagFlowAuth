from __future__ import annotations

from typing import Any


class TrainingComplianceError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


CONTROLLED_ACTIONS = {"document_review", "restore_drill_execute"}
TRAINING_OUTCOMES = {"passed", "failed"}
EFFECTIVENESS_STATUSES = {"effective", "ineffective", "pending_review"}
CERTIFICATION_STATUSES = {"active", "revoked", "suspended", "expired"}


def require_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise TrainingComplianceError(f"{field_name}_required", status_code=400)
    return text


def optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def require_known_value(value: Any, *, field_name: str, allowed: set[str]) -> str:
    text = str(value or "").strip().lower()
    if text not in allowed:
        raise TrainingComplianceError(f"invalid_{field_name}", status_code=400)
    return text


def require_positive_int(value: Any, field_name: str) -> int:
    try:
        number = int(value)
    except Exception as exc:
        raise TrainingComplianceError(f"invalid_{field_name}", status_code=400) from exc
    if number <= 0:
        raise TrainingComplianceError(f"invalid_{field_name}", status_code=400)
    return number


def require_bool(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int) and value in (0, 1):
        return value
    raise TrainingComplianceError(f"invalid_{field_name}", status_code=400)


def serialize_requirement(row: Any) -> dict[str, Any]:
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


def serialize_training_record(row: Any) -> dict[str, Any]:
    return {
        "record_id": str(row["record_id"]),
        "requirement_code": str(row["requirement_code"]),
        "user_id": str(row["user_id"]),
        "curriculum_version": str(row["curriculum_version"]),
        "trainer_user_id": str(row["trainer_user_id"]),
        "training_outcome": str(row["training_outcome"]),
        "effectiveness_status": str(row["effectiveness_status"]),
        "effectiveness_score": (
            float(row["effectiveness_score"])
            if row["effectiveness_score"] is not None
            else None
        ),
        "effectiveness_summary": str(row["effectiveness_summary"]),
        "training_notes": (str(row["training_notes"]) if row["training_notes"] else None),
        "completed_at_ms": int(row["completed_at_ms"] or 0),
        "effectiveness_reviewed_by_user_id": (
            str(row["effectiveness_reviewed_by_user_id"])
            if row["effectiveness_reviewed_by_user_id"]
            else None
        ),
        "effectiveness_reviewed_at_ms": (
            int(row["effectiveness_reviewed_at_ms"])
            if row["effectiveness_reviewed_at_ms"] is not None
            else None
        ),
        "created_at_ms": int(row["created_at_ms"] or 0),
        "updated_at_ms": int(row["updated_at_ms"] or 0),
    }


def serialize_certification(row: Any) -> dict[str, Any]:
    return {
        "certification_id": str(row["certification_id"]),
        "requirement_code": str(row["requirement_code"]),
        "user_id": str(row["user_id"]),
        "curriculum_version": str(row["curriculum_version"]),
        "certification_status": str(row["certification_status"]),
        "granted_by_user_id": str(row["granted_by_user_id"]),
        "valid_until_ms": int(row["valid_until_ms"] or 0),
        "exception_release_ref": (
            str(row["exception_release_ref"]) if row["exception_release_ref"] else None
        ),
        "certification_notes": (
            str(row["certification_notes"]) if row["certification_notes"] else None
        ),
        "granted_at_ms": int(row["granted_at_ms"] or 0),
        "revoked_at_ms": (
            int(row["revoked_at_ms"]) if row["revoked_at_ms"] is not None else None
        ),
        "created_at_ms": int(row["created_at_ms"] or 0),
        "updated_at_ms": int(row["updated_at_ms"] or 0),
    }
