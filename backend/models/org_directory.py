from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OrgDirectoryCreateRequest(BaseModel):
    name: str


class OrgDirectoryUpdateRequest(BaseModel):
    name: str


class OrgCompanyItem(BaseModel):
    id: int
    name: str
    source_key: Optional[str] = None
    created_at_ms: int
    updated_at_ms: int
    tenant_db_path: Optional[str] = None


class OrgDepartmentItem(BaseModel):
    id: int
    name: str
    path_name: str
    company_id: Optional[int] = None
    parent_department_id: Optional[int] = None
    source_key: Optional[str] = None
    source_department_id: Optional[str] = None
    level_no: int
    sort_order: int
    created_at_ms: int
    updated_at_ms: int


class OrgTreeNode(BaseModel):
    id: int
    node_type: str
    name: str
    path_name: str
    source_key: Optional[str] = None
    company_id: Optional[int] = None
    department_id: Optional[int] = None
    parent_department_id: Optional[int] = None
    level_no: int
    source_department_id: Optional[str] = None
    employee_user_id: Optional[str] = None
    email: Optional[str] = None
    employee_no: Optional[str] = None
    department_manager_name: Optional[str] = None
    is_department_manager: bool = False
    created_at_ms: int
    updated_at_ms: int
    children: list["OrgTreeNode"] = Field(default_factory=list)


class OrgStructureRebuildResponse(BaseModel):
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


class OrgDirectoryAuditLogResponse(BaseModel):
    id: int
    entity_type: str
    action: str
    entity_id: Optional[int] = None
    before_name: Optional[str] = None
    after_name: Optional[str] = None
    actor_user_id: str
    actor_username: Optional[str] = None
    created_at_ms: int


OrgTreeNode.model_rebuild()
