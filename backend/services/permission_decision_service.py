from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from backend.app.core.permission_resolver import (
    PermissionSnapshot,
    ResourceScope,
    normalize_accessible_chat_ids,
    resolve_permissions,
)


@dataclass
class PermissionDecisionError(Exception):
    reason: str
    status_code: int = 403
    code: str = "permission_denied"

    def __str__(self) -> str:
        return self.reason


class PermissionDecisionService:
    """
    Centralized authorization decision service.

    Notes:
    - Reuses resolver semantics as the single source of truth.
    - Raises PermissionDecisionError with stable reason codes used by routers.
    """

    def resolve_snapshot(self, deps: Any, user: Any) -> PermissionSnapshot:
        return resolve_permissions(deps, user)

    def ensure_admin(self, snapshot: PermissionSnapshot) -> None:
        if not snapshot.is_admin:
            raise PermissionDecisionError("admin_required")

    def ensure_chat_access(self, snapshot: PermissionSnapshot, chat_id: str) -> None:
        if snapshot.chat_scope == ResourceScope.ALL:
            return
        if snapshot.chat_scope == ResourceScope.NONE:
            raise PermissionDecisionError("no_chat_permission")
        allowed_raw_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
        if str(chat_id or "") not in allowed_raw_ids:
            raise PermissionDecisionError("no_chat_permission")

    def ensure_kb_access(self, snapshot: PermissionSnapshot, kb_ref: str | Iterable[str]) -> None:
        if snapshot.kb_scope == ResourceScope.ALL:
            return
        if snapshot.kb_scope == ResourceScope.NONE:
            raise PermissionDecisionError("kb_not_allowed")
        if isinstance(kb_ref, str):
            candidates = {kb_ref}
        else:
            candidates = {str(item).strip() for item in kb_ref if str(item).strip()}
        if not candidates.intersection(snapshot.kb_names):
            raise PermissionDecisionError("kb_not_allowed")
