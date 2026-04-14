from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from backend.app.core.tool_catalog import ASSIGNABLE_TOOL_IDS


class ResourceScope(str, Enum):
    ALL = "ALL"
    SET = "SET"
    NONE = "NONE"


QUALITY_CAPABILITY_ACTIONS: dict[str, tuple[str, ...]] = {
    "quality_system": ("view", "manage"),
    "document_control": ("create", "review", "approve", "effective", "obsolete", "publish", "export"),
    "training_ack": ("assign", "acknowledge", "review_questions"),
    "change_control": ("create", "evaluate", "approve", "plan", "confirm", "close"),
    "equipment_lifecycle": ("create", "accept", "maintain", "meter", "retire"),
    "metrology": ("record", "confirm", "approve"),
    "maintenance": ("plan", "record", "approve"),
    "batch_records": ("template_manage", "execute", "sign", "review", "export"),
    "audit_events": ("view", "export"),
    "complaints": ("view", "create", "assess", "close"),
    "capa": ("view", "create", "verify", "close"),
    "internal_audit": ("view", "create", "complete"),
    "management_review": ("view", "create", "complete"),
}


def _normalize_capability_targets(values: Iterable[str]) -> list[str]:
    targets: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if value:
            targets.add(value)
    return sorted(targets)


def _boolean_capability(enabled: bool) -> dict[str, Any]:
    return {
        "scope": "all" if enabled else "none",
        "targets": [],
    }


def _scoped_capability(scope: ResourceScope, targets: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "scope": str(scope.value).lower(),
        "targets": _normalize_capability_targets(targets) if scope == ResourceScope.SET else [],
    }


def _quality_capability_map(*, is_admin: bool, can_manage_users: bool) -> dict[str, dict[str, Any]]:
    capabilities: dict[str, dict[str, Any]] = {}

    for resource, actions in QUALITY_CAPABILITY_ACTIONS.items():
        action_map: dict[str, Any] = {}
        for action in actions:
            enabled = False
            if resource == "quality_system":
                if action == "view":
                    enabled = is_admin or can_manage_users
                elif action == "manage":
                    enabled = is_admin
            elif is_admin or can_manage_users:
                enabled = True
            elif resource == "training_ack" and action == "acknowledge":
                # Training acknowledgment is a user action; keep it enabled without granting management actions.
                enabled = True
            action_map[action] = _boolean_capability(enabled)
        capabilities[resource] = action_map

    return capabilities


@dataclass(frozen=True)
class PermissionSnapshot:
    is_admin: bool
    can_upload: bool
    can_review: bool
    can_download: bool
    can_copy: bool
    can_delete: bool
    can_manage_kb_directory: bool
    can_view_kb_config: bool
    can_view_tools: bool
    kb_scope: ResourceScope
    kb_names: frozenset[str]
    chat_scope: ResourceScope
    chat_ids: frozenset[str]
    tool_scope: ResourceScope
    tool_ids: frozenset[str]
    can_manage_users: bool = False

    def permissions_dict(self) -> dict[str, Any]:
        accessible_tools = []
        if self.tool_scope == ResourceScope.ALL:
            accessible_tools = list(ASSIGNABLE_TOOL_IDS)
        elif self.tool_scope == ResourceScope.SET:
            accessible_tools = sorted(self.tool_ids)
        return {
            "can_upload": self.can_upload,
            "can_review": self.can_review,
            "can_download": self.can_download,
            "can_copy": self.can_copy,
            "can_delete": self.can_delete,
            "can_manage_kb_directory": self.can_manage_kb_directory,
            "can_view_kb_config": self.can_view_kb_config,
            "can_view_tools": self.can_view_tools,
            "accessible_tools": accessible_tools,
        }

    def capabilities_dict(
        self,
        *,
        accessible_kb_ids: Iterable[str] = (),
        accessible_chat_ids: Iterable[str] = (),
    ) -> dict[str, dict[str, dict[str, Any]]]:
        kb_targets = _normalize_capability_targets(accessible_kb_ids)
        chat_targets = _normalize_capability_targets(accessible_chat_ids)
        tool_targets = _normalize_capability_targets(self.tool_ids)

        return {
            "users": {
                "manage": _boolean_capability(self.is_admin or self.can_manage_users),
            },
            "kb_documents": {
                "view": _scoped_capability(self.kb_scope, kb_targets),
                "upload": _boolean_capability(self.can_upload),
                "review": _boolean_capability(self.can_review),
                "approve": _boolean_capability(self.can_review),
                "reject": _boolean_capability(self.can_review),
                "delete": _boolean_capability(self.can_delete),
                "download": _boolean_capability(self.can_download),
                "copy": _boolean_capability(self.can_copy),
            },
            "ragflow_documents": {
                "view": _scoped_capability(self.kb_scope, kb_targets),
                "preview": _scoped_capability(self.kb_scope, kb_targets),
                "delete": _boolean_capability(self.can_delete),
                "download": _boolean_capability(self.can_download),
                "copy": _boolean_capability(self.can_copy),
            },
            "kb_directory": {
                "manage": _boolean_capability(self.can_manage_kb_directory),
            },
            "kbs_config": {
                "view": _boolean_capability(self.can_view_kb_config),
            },
            "tools": {
                "view": _scoped_capability(self.tool_scope, tool_targets),
            },
            "chats": {
                "view": _scoped_capability(self.chat_scope, chat_targets),
            },
            **_quality_capability_map(
                is_admin=self.is_admin,
                can_manage_users=self.can_manage_users,
            ),
        }


@dataclass
class PermissionAccumulator:
    can_upload: bool = False
    can_review: bool = False
    can_download: bool = False
    can_copy: bool = False
    can_delete: bool = False
    can_manage_kb_directory: bool = False
    can_view_kb_config: bool = False
    can_view_tools: bool = False
    can_manage_users: bool = False
    kb_names: set[str] = field(default_factory=set)
    kb_node_ids: set[str] = field(default_factory=set)
    chat_ids: set[str] = field(default_factory=set)
    tool_ids: set[str] = field(default_factory=set)
    tool_has_global_access: bool = False
    tool_has_scoped_access: bool = False
