from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Company:
    company_id: int
    name: str
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class Department:
    department_id: int
    name: str
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class OrgDirectoryAuditLog:
    id: int
    entity_type: str
    action: str
    entity_id: Optional[int]
    before_name: Optional[str]
    after_name: Optional[str]
    actor_user_id: str
    created_at_ms: int

