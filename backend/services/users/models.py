from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    manager_user_id: Optional[str] = None
    employee_user_id: Optional[str] = None
    role: str = "viewer"
    # Deprecated: single group id, kept for compatibility.
    group_id: Optional[int] = None
    company_id: Optional[int] = None
    department_id: Optional[int] = None
    # Per-account login policy.
    max_login_sessions: int = 3
    idle_timeout_minutes: int = 120
    can_change_password: bool = True
    disable_login_enabled: bool = False
    disable_login_until_ms: Optional[int] = None
    # Source of truth permission groups.
    group_ids: List[int] | None = None
    tool_ids: List[str] | None = None
    status: str = "active"
    created_at_ms: int = 0
    last_login_at_ms: Optional[int] = None
    created_by: Optional[str] = None
    managed_kb_root_node_id: Optional[str] = None
    electronic_signature_enabled: bool = True
    password_changed_at_ms: Optional[int] = None
    credential_fail_count: int = 0
    credential_fail_window_started_at_ms: Optional[int] = None
    credential_locked_until_ms: Optional[int] = None

    def __post_init__(self):
        if self.group_ids is None:
            self.group_ids = []
        if self.tool_ids is None:
            self.tool_ids = []
