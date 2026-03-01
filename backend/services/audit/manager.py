from __future__ import annotations

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
                    "source": r.source,
                    "doc_id": r.doc_id,
                    "filename": r.filename,
                    "kb_id": r.kb_id,
                    "kb_dataset_id": r.kb_dataset_id,
                    "kb_name": r.kb_name,
                    "meta_json": r.meta_json,
                }
                for r in rows
            ],
        }
