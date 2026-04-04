from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.signature_support import resolve_signature_service
from backend.database.tenant_paths import resolve_tenant_db_root
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.electronic_signature import ElectronicSignatureError
from backend.services.audit_helpers import actor_fields_from_user
from backend.services.user_store import UserStore


router = APIRouter()


class ElectronicSignatureAuthorizationUpdateRequest(BaseModel):
    electronic_signature_enabled: bool


def _resolve_signature_full_name(ctx: AuthContextDep, service: ElectronicSignatureService, signature) -> str | None:
    db_path = getattr(getattr(service, "_store", None), "db_path", None)
    candidates: list[object] = []

    if db_path:
        try:
            candidates.append(UserStore(db_path=str(db_path)))
        except Exception:
            pass

    primary_store = getattr(ctx.deps, "user_store", None)
    if primary_store is not None:
        candidates.append(primary_store)

    seen_store_ids: set[int] = set()
    for store in candidates:
        if id(store) in seen_store_ids:
            continue
        seen_store_ids.add(id(store))
        try:
            user = store.get_by_user_id(str(signature.signed_by))
        except Exception:
            user = None
        full_name = getattr(user, "full_name", None) if user is not None else None
        normalized = str(full_name or "").strip()
        if normalized:
            return normalized
    return None


def _signature_to_dict(ctx: AuthContextDep, signature, service: ElectronicSignatureService, *, verified: bool | None = None):
    payload = {
        "signature_id": signature.signature_id,
        "record_type": signature.record_type,
        "record_id": signature.record_id,
        "action": signature.action,
        "meaning": signature.meaning,
        "reason": signature.reason,
        "signed_by": signature.signed_by,
        "signed_by_username": signature.signed_by_username,
        "signed_by_full_name": _resolve_signature_full_name(ctx, service, signature),
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


def _base_signature_db_path(ctx: AuthContextDep) -> str | None:
    for attr_name in ("electronic_signature_store", "user_store", "kb_store"):
        store = getattr(ctx.deps, attr_name, None)
        db_path = getattr(store, "db_path", None)
        if db_path:
            return str(db_path)
    return None


def _company_id_from_db_path(base_db_path: str | None, db_path: str | None) -> int | None:
    if not base_db_path or not db_path:
        return None
    try:
        root = resolve_tenant_db_root(base_db_path=base_db_path)
        candidate = Path(db_path).resolve()
        root_resolved = root.resolve()
        if root_resolved not in candidate.parents:
            return None
        tenant_dir = candidate.parent.name
        if not tenant_dir.startswith("company_"):
            return None
        return int(tenant_dir.split("_", 1)[1])
    except Exception:
        return None


def _iter_signature_services(ctx: AuthContextDep) -> list[tuple[ElectronicSignatureService, int | None]]:
    base_db_path = _base_signature_db_path(ctx)
    current_service = resolve_signature_service(ctx.deps)
    current_db_path = getattr(getattr(current_service, "_store", None), "db_path", None)
    seen_paths: set[str] = set()
    items: list[tuple[ElectronicSignatureService, int | None]] = []

    if current_db_path:
        normalized = str(Path(current_db_path).resolve())
        seen_paths.add(normalized)
    items.append((current_service, _company_id_from_db_path(base_db_path, current_db_path)))

    if not base_db_path:
        return items

    tenant_root = resolve_tenant_db_root(base_db_path=base_db_path)
    if not tenant_root.exists():
        return items

    for db_path in tenant_root.glob("company_*/auth.db"):
        normalized = str(db_path.resolve())
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=str(db_path)))
        items.append((service, _company_id_from_db_path(base_db_path, str(db_path))))
    return items


def _find_signature_across_services(ctx: AuthContextDep, signature_id: str):
    for service, company_id in _iter_signature_services(ctx):
        try:
            signature = service.get_signature(signature_id)
            return service, signature, company_id
        except ElectronicSignatureError as exc:
            if exc.code != "signature_not_found":
                raise
    raise ElectronicSignatureError("signature_not_found", status_code=404)


@router.get("/electronic-signatures")
def list_electronic_signatures(
    ctx: AuthContextDep,
    _: AdminOnly,
    record_type: str | None = None,
    action: str | None = None,
    signed_by: str | None = None,
    signed_at_from_ms: int | None = None,
    signed_at_to_ms: int | None = None,
    offset: int = 0,
    limit: int = 100,
):
    safe_offset = max(0, int(offset))
    safe_limit = max(1, min(500, int(limit)))
    all_items: list[dict] = []

    for service, company_id in _iter_signature_services(ctx):
        _, items = service.list_signatures(
            record_type=record_type,
            action=action,
            signed_by=signed_by,
            signed_at_from_ms=signed_at_from_ms,
            signed_at_to_ms=signed_at_to_ms,
            offset=0,
            limit=500,
        )
        for item in items:
            payload = _signature_to_dict(
                ctx,
                item,
                service,
                verified=bool(service.verify_signature(signature_id=item.signature_id)),
            )
            payload["company_id"] = company_id
            all_items.append(payload)

    all_items.sort(
        key=lambda item: (int(item.get("signed_at_ms") or 0), str(item.get("signature_id") or "")),
        reverse=True,
    )
    paged_items = all_items[safe_offset : safe_offset + safe_limit]
    return {
        "items": paged_items,
        "count": len(paged_items),
        "total": len(all_items),
        "offset": safe_offset,
        "limit": safe_limit,
    }


@router.get("/electronic-signature-authorizations")
def list_electronic_signature_authorizations(
    ctx: AuthContextDep,
    _: AdminOnly,
    q: str | None = None,
    status: str | None = None,
    electronic_signature_enabled: bool | None = None,
    limit: int = 100,
):
    users = ctx.deps.user_store.list_users(
        q=q,
        status=status,
        role=None,
        group_id=None,
        company_id=None,
        department_id=None,
        created_from_ms=None,
        created_to_ms=None,
        limit=max(1, min(int(limit), 500)),
    )
    items = []
    for user in users:
        enabled = bool(getattr(user, "electronic_signature_enabled", True))
        if electronic_signature_enabled is not None and enabled != bool(electronic_signature_enabled):
            continue
        items.append(
            {
                "user_id": user.user_id,
                "username": user.username,
                "full_name": getattr(user, "full_name", None),
                "role": getattr(user, "role", None),
                "status": getattr(user, "status", None),
                "electronic_signature_enabled": enabled,
                "credential_locked_until_ms": getattr(user, "credential_locked_until_ms", None),
                "last_login_at_ms": getattr(user, "last_login_at_ms", None),
            }
        )
    return {
        "items": items,
        "count": len(items),
    }


@router.put("/electronic-signature-authorizations/{user_id}")
def update_electronic_signature_authorization(
    user_id: str,
    body: ElectronicSignatureAuthorizationUpdateRequest,
    ctx: AuthContextDep,
    request: Request,
    _: AdminOnly,
):
    existing = ctx.deps.user_store.get_by_user_id(user_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    updated = ctx.deps.user_store.update_user(
        user_id=user_id,
        electronic_signature_enabled=body.electronic_signature_enabled,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    audit = getattr(ctx.deps, "audit_log_manager", None)
    if audit is not None:
        audit.log_event(
            action="electronic_signature_authorization_update",
            actor=ctx.user.user_id,
            source="electronic_signature",
            resource_type="user",
            resource_id=updated.user_id,
            event_type="update",
            before={"electronic_signature_enabled": bool(getattr(existing, "electronic_signature_enabled", True))},
            after={"electronic_signature_enabled": bool(getattr(updated, "electronic_signature_enabled", True))},
            request_id=getattr(getattr(request, "state", None), "request_id", None),
            client_ip=getattr(getattr(request, "client", None), "host", None),
            meta={"target_username": updated.username},
            **actor_fields_from_user(ctx.deps, ctx.user),
        )
    return {
        "user_id": updated.user_id,
        "username": updated.username,
        "electronic_signature_enabled": bool(getattr(updated, "electronic_signature_enabled", True)),
    }


@router.get("/electronic-signatures/{signature_id}")
def get_electronic_signature(
    signature_id: str,
    ctx: AuthContextDep,
    _: AdminOnly,
):
    try:
        service, signature, company_id = _find_signature_across_services(ctx, signature_id)
        result = _signature_to_dict(ctx, signature, service)
        result["company_id"] = company_id
        result["verified"] = bool(service.verify_signature(signature_id=signature_id))
        return result
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post("/electronic-signatures/{signature_id}/verify")
def verify_electronic_signature(
    signature_id: str,
    ctx: AuthContextDep,
    _: AdminOnly,
):
    try:
        service, signature, company_id = _find_signature_across_services(ctx, signature_id)
        return {
            "signature_id": signature.signature_id,
            "company_id": company_id,
            "verified": bool(service.verify_signature(signature_id=signature_id)),
        }
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
