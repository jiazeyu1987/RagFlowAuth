from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Company:
    company_id: int
    name: str
    source_key: Optional[str]
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class Department:
    department_id: int
    name: str
    company_id: Optional[int]
    parent_department_id: Optional[int]
    source_key: Optional[str]
    source_department_id: Optional[str]
    level_no: int
    path_name: str
    sort_order: int
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class Employee:
    employee_id: int
    employee_user_id: str
    name: str
    email: Optional[str]
    employee_no: Optional[str]
    department_manager_name: Optional[str]
    is_department_manager: bool
    company_id: Optional[int]
    department_id: Optional[int]
    source_key: str
    sort_order: int
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


@dataclass(frozen=True)
class OrgStructureRebuildSummary:
    excel_path: str
    company_count: int
    department_count: int
    employee_count: int
    companies_created: int
    companies_updated: int
    companies_deleted: int
    departments_created: int
    departments_updated: int
    departments_deleted: int
    employees_created: int
    employees_updated: int
    employees_deleted: int
    users_company_cleared: int
    users_department_cleared: int
    completed_at_ms: int
