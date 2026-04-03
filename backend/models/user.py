from typing import List, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    manager_user_id: Optional[str] = None
    company_id: Optional[int] = None
    department_id: Optional[int] = None
    role: Optional[str] = None
    # Deprecated: single group id, kept for compatibility.
    group_id: Optional[int] = None
    group_ids: Optional[List[int]] = None
    status: str = "active"
    # Per-account login policy.
    max_login_sessions: int = 3
    idle_timeout_minutes: int = 120
    can_change_password: bool = True
    disable_login_enabled: bool = False
    disable_login_until_ms: Optional[int] = None
    managed_kb_root_node_id: Optional[str] = None
    electronic_signature_enabled: bool = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    manager_user_id: Optional[str] = None
    company_id: Optional[int] = None
    department_id: Optional[int] = None
    role: Optional[str] = None
    group_id: Optional[int] = None
    group_ids: Optional[List[int]] = None
    status: Optional[str] = None
    max_login_sessions: Optional[int] = None
    idle_timeout_minutes: Optional[int] = None
    can_change_password: Optional[bool] = None
    disable_login_enabled: Optional[bool] = None
    disable_login_until_ms: Optional[int] = None
    managed_kb_root_node_id: Optional[str] = None
    electronic_signature_enabled: Optional[bool] = None


class UserResponse(BaseModel):
    user_id: str
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    manager_user_id: Optional[str] = None
    manager_username: Optional[str] = None
    manager_full_name: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    group_id: Optional[int] = None
    group_ids: List[int] = Field(default_factory=list)
    group_name: Optional[str] = None
    permission_groups: List[dict] = Field(default_factory=list)
    role: str
    status: str
    can_change_password: bool = True
    disable_login_enabled: bool = False
    disable_login_until_ms: Optional[int] = None
    login_disabled: bool = False
    max_login_sessions: int
    idle_timeout_minutes: int
    active_session_count: int = 0
    active_session_last_activity_at_ms: Optional[int] = None
    created_at_ms: int
    last_login_at_ms: Optional[int] = None
    managed_kb_root_node_id: Optional[str] = None
    managed_kb_root_path: Optional[str] = None
    electronic_signature_enabled: bool = True
