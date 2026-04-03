from __future__ import annotations

from fastapi import HTTPException

from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore


def resolve_signature_service(deps) -> ElectronicSignatureService:
    service = getattr(deps, "electronic_signature_service", None)
    if service is not None:
        return service

    for attr_name in ("kb_store", "user_store"):
        store = getattr(deps, attr_name, None)
        db_path = getattr(store, "db_path", None)
        if db_path:
            return ElectronicSignatureService(store=ElectronicSignatureStore(db_path=str(db_path)))

    raise HTTPException(status_code=500, detail="electronic_signature_service_unavailable")


def effective_review_notes(review_data) -> str | None:
    if review_data is None:
        return None

    review_notes = getattr(review_data, "review_notes", None)
    if review_notes is not None:
        normalized = str(review_notes).strip()
        if normalized:
            return normalized

    signature_reason = getattr(review_data, "signature_reason", None)
    if signature_reason is None:
        return None
    normalized_reason = str(signature_reason).strip()
    return normalized_reason or None


def signature_manifestation_payload(signature, *, verified: bool | None = None) -> dict | None:
    if signature is None:
        return None
    payload = {
        "signature_id": getattr(signature, "signature_id", None),
        "signature_action": getattr(signature, "action", None),
        "signature_meaning": getattr(signature, "meaning", None),
        "signature_reason": getattr(signature, "reason", None),
        "signed_by": getattr(signature, "signed_by", None),
        "signed_by_username": getattr(signature, "signed_by_username", None),
        "signed_at_ms": getattr(signature, "signed_at_ms", None),
        "sign_token_id": getattr(signature, "sign_token_id", None),
        "signature_status": getattr(signature, "status", None),
    }
    if verified is not None:
        payload["signature_verified"] = bool(verified)
    return payload
