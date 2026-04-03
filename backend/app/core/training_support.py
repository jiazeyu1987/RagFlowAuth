from __future__ import annotations

from fastapi import HTTPException

from backend.services.training_compliance import TrainingComplianceError


def resolve_training_compliance_service(deps):
    service = getattr(deps, "training_compliance_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="training_compliance_service_unavailable")
    return service


def assert_user_training_for_action(*, deps, user, controlled_action: str) -> dict:
    service = resolve_training_compliance_service(deps)
    try:
        return service.assert_user_authorized_for_action(
            user_id=str(getattr(user, "user_id", "") or ""),
            role_code=str(getattr(user, "role", "") or ""),
            controlled_action=controlled_action,
        )
    except TrainingComplianceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
