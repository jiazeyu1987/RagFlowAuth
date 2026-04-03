from __future__ import annotations

from backend.services.training_compliance import TrainingComplianceService


ACTION_REQUIREMENT_CODES = {
    "document_review": "TR-001",
    "restore_drill_execute": "TR-002",
}


def qualify_user_for_action(
    db_path: str,
    *,
    user_id: str,
    action_code: str,
    trainer_user_id: str = "admin-1",
    granted_by_user_id: str = "admin-1",
    completed_at_ms: int = 1_800_000_000_000,
    valid_until_ms: int | None = None,
    effectiveness_status: str = "effective",
    training_outcome: str = "passed",
) -> dict:
    service = TrainingComplianceService(db_path=db_path)
    requirement_code = ACTION_REQUIREMENT_CODES[action_code]
    requirement = service.get_requirement(requirement_code)
    record = service.record_training(
        requirement_code=requirement_code,
        user_id=user_id,
        curriculum_version=requirement["curriculum_version"],
        trainer_user_id=trainer_user_id,
        training_outcome=training_outcome,
        effectiveness_status=effectiveness_status,
        effectiveness_score=100.0 if effectiveness_status == "effective" else 40.0,
        effectiveness_summary="自动化测试录入的培训有效性记录",
        training_notes="test qualification seed",
        completed_at_ms=completed_at_ms,
        effectiveness_reviewed_by_user_id=granted_by_user_id if effectiveness_status != "pending_review" else None,
        effectiveness_reviewed_at_ms=completed_at_ms if effectiveness_status != "pending_review" else None,
    )
    certification = service.grant_certification(
        requirement_code=requirement_code,
        user_id=user_id,
        granted_by_user_id=granted_by_user_id,
        certification_status="active",
        valid_until_ms=valid_until_ms,
        certification_notes="test certification seed",
        granted_at_ms=completed_at_ms,
    )
    return {
        "requirement": requirement,
        "record": record,
        "certification": certification,
    }
