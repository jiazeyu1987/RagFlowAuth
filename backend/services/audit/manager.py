from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.services.audit_helpers import actor_fields_from_ctx


@dataclass
class AuditLogError(Exception):
    code: str
    status_code: int = 500

    def __str__(self) -> str:
        return self.code


class AuditLogManager:
    """
    Shared audit logging facade.

    - keeps store access out of routers/domain services
    - provides ctx-aware best-effort logging
    - provides query formatting for audit API
    """

    def __init__(self, store: Any):
        self._store = store

    def log_event(self, **kwargs):
        if self._store is None:
            return None
        return self._store.log_event(**kwargs)

    def log_ctx_event(self, *, ctx: Any, action: str, source: str, meta: dict[str, Any] | None = None, **kwargs):
        if self._store is None:
            return None
        return self._store.log_event(
            action=action,
            actor=ctx.payload.sub,
            source=source,
            meta=meta,
            **kwargs,
            **actor_fields_from_ctx(ctx.deps, ctx),
        )

    def log_record_change(
        self,
        *,
        ctx: Any,
        action: str,
        source: str,
        resource_type: str,
        resource_id: str,
        event_type: str,
        before: Any | None,
        after: Any | None,
        reason: str | None = None,
        signature_id: str | None = None,
        request_id: str | None = None,
        client_ip: str | None = None,
        meta: dict[str, Any] | None = None,
        **kwargs,
    ):
        return self.log_ctx_event(
            ctx=ctx,
            action=action,
            source=source,
            resource_type=resource_type,
            resource_id=resource_id,
            event_type=event_type,
            before=before,
            after=after,
            reason=reason,
            signature_id=signature_id,
            request_id=request_id,
            client_ip=client_ip,
            meta=meta,
            **kwargs,
        )

    def safe_log_ctx_event(self, *, ctx: Any, action: str, source: str, meta: dict[str, Any] | None = None, **kwargs) -> None:
        try:
            self.log_ctx_event(ctx=ctx, action=action, source=source, meta=meta, **kwargs)
        except Exception:
            return None

    def list_events(self, **kwargs) -> dict[str, Any]:
        if self._store is None:
            return {"total": 0, "items": []}
        total, rows = self._store.list_events(**kwargs)
        return {
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "action": r.action,
                    "actor": r.actor,
                    "username": r.actor_username,
                    "company_id": r.company_id,
                    "company_name": r.company_name,
                    "department_id": r.department_id,
                    "department_name": r.department_name,
                    "created_at_ms": r.created_at_ms,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "event_type": r.event_type,
                    "before": _decode_meta_json(r.before_json),
                    "after": _decode_meta_json(r.after_json),
                    "before_json": r.before_json,
                    "after_json": r.after_json,
                    "reason": r.reason,
                    "signature_id": r.signature_id,
                    "request_id": r.request_id,
                    "client_ip": r.client_ip,
                    "prev_hash": r.prev_hash,
                    "event_hash": r.event_hash,
                    "source": r.source,
                    "doc_id": r.doc_id,
                    "filename": r.filename,
                    "kb_id": r.kb_id,
                    "kb_dataset_id": r.kb_dataset_id,
                    "kb_name": r.kb_name,
                    "meta": _decode_meta_json(r.meta_json),
                    "meta_json": r.meta_json,
                }
                for r in rows
            ],
        }


def _decode_meta_json(meta_json: str | None) -> Any:
    if not meta_json:
        return None
    try:
        return json.loads(meta_json)
    except Exception:
        return None
