from __future__ import annotations

from copy import deepcopy
from typing import Any


AVAILABLE_CHANNEL_TYPES = ("email", "dingtalk", "in_app")

_EVENT_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "group_key": "document_review",
        "group_label": "\u6587\u6863\u5ba1\u6838",
        "items": (
            {"event_type": "review_todo_approval", "event_label": "\u5f85\u5ba1\u6838\u901a\u77e5"},
            {"event_type": "review_approved", "event_label": "\u5ba1\u6838\u901a\u8fc7\u901a\u77e5"},
            {"event_type": "review_rejected", "event_label": "\u5ba1\u6838\u9a73\u56de\u901a\u77e5"},
        ),
    },
    {
        "group_key": "operation_approval",
        "group_label": "\u64cd\u4f5c\u5ba1\u6279",
        "items": (
            {"event_type": "operation_approval_submitted", "event_label": "\u7533\u8bf7\u5df2\u63d0\u4ea4"},
            {"event_type": "operation_approval_todo", "event_label": "\u5ba1\u6279\u5f85\u5904\u7406"},
            {"event_type": "operation_approval_rejected", "event_label": "\u7533\u8bf7\u5df2\u9a73\u56de"},
            {"event_type": "operation_approval_withdrawn", "event_label": "\u7533\u8bf7\u5df2\u64a4\u56de"},
            {"event_type": "operation_approval_executed", "event_label": "\u7533\u8bf7\u5df2\u6267\u884c"},
            {"event_type": "operation_approval_execution_failed", "event_label": "\u7533\u8bf7\u6267\u884c\u5931\u8d25"},
        ),
    },
    {
        "group_key": "account_security",
        "group_label": "\u8d26\u53f7\u5b89\u5168",
        "items": (
            {"event_type": "credential_lockout", "event_label": "\u51ed\u8bc1\u9501\u5b9a\u544a\u8b66"},
        ),
    },
    {
        "group_key": "quality_system",
        "group_label": "\u8d28\u91cf\u4f53\u7cfb",
        "items": (
            {"event_type": "equipment_due_soon", "event_label": "\u8bbe\u5907\u4e34\u671f\u63d0\u9192"},
            {"event_type": "metrology_due_soon", "event_label": "\u8ba1\u91cf\u4e34\u671f\u63d0\u9192"},
            {"event_type": "maintenance_due_soon", "event_label": "\u7ef4\u62a4\u4fdd\u517b\u4e34\u671f\u63d0\u9192"},
        ),
    },
)

_EVENT_META_BY_TYPE: dict[str, dict[str, str]] = {}
for group in _EVENT_GROUPS:
    for item in group.get("items") or ():
        _EVENT_META_BY_TYPE[str(item["event_type"])] = {
            "group_key": str(group["group_key"]),
            "group_label": str(group["group_label"]),
            "event_type": str(item["event_type"]),
            "event_label": str(item["event_label"]),
        }


SUPPORTED_EVENT_TYPES = frozenset(_EVENT_META_BY_TYPE.keys())


def list_event_groups() -> list[dict[str, Any]]:
    return deepcopy(list(_EVENT_GROUPS))


def get_event_meta(event_type: str) -> dict[str, str] | None:
    key = str(event_type or "").strip()
    meta = _EVENT_META_BY_TYPE.get(key)
    if meta is None:
        return None
    return dict(meta)
