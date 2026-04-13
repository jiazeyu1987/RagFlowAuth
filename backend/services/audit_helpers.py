from __future__ import annotations

from typing import Any


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _truncate_text(value: Any, *, max_chars: int = 240) -> str:
    text = _clean_text(value)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def actor_fields_from_user(deps: Any, user: Any) -> dict[str, Any]:
    """
    Produce normalized actor fields for audit_events.

    This intentionally duplicates (denormalizes) org/user attributes into audit_events
    to make filtering/reporting simple and stable over time.
    """
    username = getattr(user, "username", None)
    company_id = getattr(user, "company_id", None)
    department_id = getattr(user, "department_id", None)
    org_structure_manager = getattr(deps, "org_structure_manager", None)

    company_name = None
    if company_id is not None and org_structure_manager is not None:
        try:
            c = org_structure_manager.get_company(int(company_id))
            company_name = getattr(c, "name", None) if c else None
        except Exception:
            company_name = None

    department_name = None
    if department_id is not None and org_structure_manager is not None:
        try:
            d = org_structure_manager.get_department(int(department_id))
            department_name = (getattr(d, "path_name", None) or getattr(d, "name", None)) if d else None
        except Exception:
            department_name = None

    return {
        "actor_username": username,
        "company_id": int(company_id) if company_id is not None else None,
        "company_name": company_name,
        "department_id": int(department_id) if department_id is not None else None,
        "department_name": department_name,
    }


def actor_fields_from_ctx(deps: Any, ctx: Any) -> dict[str, Any]:
    user = getattr(ctx, "user", None)
    if not user:
        return {
            "actor_username": None,
            "company_id": None,
            "company_name": None,
            "department_id": None,
            "department_name": None,
        }
    return actor_fields_from_user(deps, user)


def build_audit_evidence_refs(
    raw_refs: list[dict[str, Any]] | None,
    *,
    default_role: str,
    default_resource_type: str = "knowledge_document",
    max_items: int = 20,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in raw_refs or []:
        if not isinstance(raw, dict):
            continue

        resource_id = _clean_text(
            raw.get("resource_id")
            or raw.get("doc_id")
            or raw.get("document_id")
            or raw.get("documentId")
            or raw.get("docId")
            or raw.get("id")
        )
        if not resource_id:
            continue

        kb_name = _clean_text(raw.get("kb_name") or raw.get("dataset") or raw.get("dataset_name"))
        kb_id = _clean_text(raw.get("kb_id") or kb_name)
        kb_dataset_id = _clean_text(raw.get("kb_dataset_id") or raw.get("dataset_id") or kb_name)
        filename = _clean_text(
            raw.get("filename")
            or raw.get("title")
            or raw.get("name")
            or raw.get("document_name")
            or raw.get("doc_name")
        )
        storage_ref = _clean_text(raw.get("storage_ref"))
        if not storage_ref and kb_name:
            storage_ref = f"{kb_name}:{resource_id}"

        entry = {
            "attachment_id": _clean_text(raw.get("attachment_id")) or f"{default_resource_type}:{resource_id}",
            "resource_type": _clean_text(raw.get("resource_type")) or default_resource_type,
            "resource_id": resource_id,
            "filename": filename or resource_id,
            "mime_type": _clean_text(raw.get("mime_type")) or None,
            "storage_ref": storage_ref or None,
            "uploaded_by": _clean_text(raw.get("uploaded_by")) or None,
            "uploaded_at_ms": raw.get("uploaded_at_ms"),
            "evidence_role": _clean_text(raw.get("evidence_role")) or default_role,
            "doc_id": resource_id,
            "kb_id": kb_id or None,
            "kb_dataset_id": kb_dataset_id or None,
            "kb_name": kb_name or None,
            "chunk_preview": _truncate_text(raw.get("chunk") or raw.get("chunk_preview")),
        }
        normalized.append(entry)
        if len(normalized) >= max_items:
            break
    return normalized


def first_evidence_document_context(evidence_refs: list[dict[str, Any]] | None) -> dict[str, Any]:
    for item in evidence_refs or []:
        if not isinstance(item, dict):
            continue
        doc_id = _clean_text(item.get("doc_id") or item.get("resource_id"))
        if not doc_id:
            continue
        return {
            "doc_id": doc_id,
            "filename": _clean_text(item.get("filename")) or None,
            "kb_id": _clean_text(item.get("kb_id")) or None,
            "kb_dataset_id": _clean_text(item.get("kb_dataset_id")) or None,
            "kb_name": _clean_text(item.get("kb_name")) or None,
        }
    return {
        "doc_id": None,
        "filename": None,
        "kb_id": None,
        "kb_dataset_id": None,
        "kb_name": None,
    }


def log_quality_audit_event(
    *,
    deps: Any,
    ctx: Any,
    action: str,
    source: str,
    evidence_refs: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
    **kwargs,
):
    payload = {
        "action": action,
        "actor": getattr(getattr(ctx, "payload", None), "sub", None),
        "source": source,
        "meta": meta,
        "evidence_refs": evidence_refs,
        **kwargs,
        **actor_fields_from_ctx(deps, ctx),
    }

    manager = getattr(deps, "audit_log_manager", None)
    if manager is not None and hasattr(manager, "log_event"):
        return manager.log_event(**payload)

    store = getattr(deps, "audit_log_store", None)
    if store is not None and hasattr(store, "log_event"):
        return store.log_event(**payload)

    raise RuntimeError("audit_log_manager_unavailable")
