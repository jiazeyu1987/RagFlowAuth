from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.database.tenant_paths import normalize_company_id, tenant_key_for_company


def _payload_value(payload: object, key: str):
    if isinstance(payload, dict):
        return payload.get(key)
    if hasattr(payload, key):
        return getattr(payload, key)
    try:
        return payload.model_dump().get(key)  # type: ignore[attr-defined]
    except Exception:
        return None


def company_id_from_payload(payload: object | None) -> int | None:
    if payload is None:
        return None
    raw = _payload_value(payload, "cid")
    if raw is None:
        raw = _payload_value(payload, "company_id")
    if raw is None or str(raw).strip() == "":
        return None
    return normalize_company_id(raw)


def company_id_from_user(user: Any) -> int | None:
    raw = getattr(user, "company_id", None)
    if raw is None or str(raw).strip() == "":
        return None
    return normalize_company_id(raw)


@dataclass(frozen=True)
class TenantContext:
    company_id: int
    tenant_key: str


def tenant_context(company_id: int | str) -> TenantContext:
    cid = normalize_company_id(company_id)
    return TenantContext(company_id=cid, tenant_key=tenant_key_for_company(cid))
