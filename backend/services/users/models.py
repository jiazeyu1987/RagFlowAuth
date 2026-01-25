from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    email: Optional[str] = None
    role: str = "viewer"
    group_id: Optional[int] = None  # 权限组ID（已废弃，保留用于向后兼容）
    company_id: Optional[int] = None
    department_id: Optional[int] = None
    group_ids: List[int] | None = None  # 新字段：权限组ID列表
    status: str = "active"
    created_at_ms: int = 0
    last_login_at_ms: Optional[int] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        if self.group_ids is None:
            self.group_ids = []

