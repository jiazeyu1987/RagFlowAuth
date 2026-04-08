from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GroupPermissionFlags:
    can_upload: bool = False
    can_review: bool = False
    can_download: bool = False
    can_copy: bool = False
    can_delete: bool = False
    can_manage_kb_directory: bool = False
    can_view_kb_config: bool = False
    can_view_tools: bool = False


def _group_flag(group: Any, key: str, *, default: bool) -> bool:
    if not isinstance(group, dict):
        return default
    return bool(group.get(key, default))


def resolve_group_permission_flags(group: Any) -> GroupPermissionFlags:
    return GroupPermissionFlags(
        can_upload=_group_flag(group, "can_upload", default=False),
        can_review=_group_flag(group, "can_review", default=False),
        can_download=_group_flag(group, "can_download", default=False),
        can_copy=_group_flag(group, "can_copy", default=False),
        can_delete=_group_flag(group, "can_delete", default=False),
        can_manage_kb_directory=_group_flag(group, "can_manage_kb_directory", default=False),
        # Legacy policy: missing flags were historically treated as allowed.
        can_view_kb_config=_group_flag(group, "can_view_kb_config", default=True),
        can_view_tools=_group_flag(group, "can_view_tools", default=True),
    )
