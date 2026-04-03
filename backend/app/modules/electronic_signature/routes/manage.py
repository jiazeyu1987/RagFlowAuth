from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.signature_support import resolve_signature_service


router = APIRouter()


def _signature_to_dict(signature, *, verified: bool | None = None):
    payload = {
        "signature_id": signature.signature_id,
        "record_type": signature.record_type,
        "record_id": signature.record_id,
        "action": signature.action,
        "meaning": signature.meaning,
        "reason": signature.reason,
        "signed_by": signature.signed_by,
        "signed_by_username": signature.signed_by_username,
        "signed_at_ms": signature.signed_at_ms,
        "sign_token_id": signature.sign_token_id,
        "record_hash": signature.record_hash,
        "signature_hash": signature.signature_hash,
        "status": signature.status,
        "record_payload": signature.record_payload,
        "record_payload_json": signature.record_payload_json,
    }
    if verified is not None:
        payload["verified"] = bool(verified)
    return payload


@router.get("/electronic-signatures")
def list_electronic_signatures(
    ctx: AuthContextDep,
    _: AdminOnly,
    record_type: str | None = None,
    record_id: str | None = None,
    action: str | None = None,
    signed_by: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 100,
):
    service = resolve_signature_service(ctx.deps)
    total, items = service.list_signatures(
        record_type=record_type,
        record_id=record_id,
        action=action,
        signed_by=signed_by,
        status=status,
        offset=offset,
        limit=limit,
    )
    verified_map = {
        item.signature_id: bool(service.verify_signature(signature_id=item.signature_id))
        for item in items
    }
    return {
        "items": [_signature_to_dict(item, verified=verified_map.get(item.signature_id)) for item in items],
        "count": len(items),
        "total": total,
        "offset": max(0, int(offset)),
        "limit": max(1, min(500, int(limit))),
    }


@router.get("/electronic-signatures/{signature_id}")
def get_electronic_signature(
    signature_id: str,
    ctx: AuthContextDep,
    _: AdminOnly,
):
    service = resolve_signature_service(ctx.deps)
    signature = service.get_signature(signature_id)
    result = _signature_to_dict(signature)
    result["verified"] = bool(service.verify_signature(signature_id=signature_id))
    return result


@router.post("/electronic-signatures/{signature_id}/verify")
def verify_electronic_signature(
    signature_id: str,
    ctx: AuthContextDep,
    _: AdminOnly,
):
    service = resolve_signature_service(ctx.deps)
    signature = service.get_signature(signature_id)
    return {
        "signature_id": signature.signature_id,
        "verified": bool(service.verify_signature(signature_id=signature_id)),
    }
