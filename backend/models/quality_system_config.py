from __future__ import annotations

from pydantic import BaseModel, Field


class QualitySystemAssignableUser(BaseModel):
    user_id: str
    username: str
    full_name: str | None = None
    employee_user_id: str | None = None
    status: str
    company_id: int | None = None
    company_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None


class QualitySystemPosition(BaseModel):
    id: int
    name: str
    in_signoff: bool
    in_compiler: bool
    in_approver: bool
    seeded_from_json: bool
    assigned_users: list[QualitySystemAssignableUser] = Field(default_factory=list)


class QualitySystemFileCategory(BaseModel):
    id: int
    name: str
    seeded_from_json: bool
    is_active: bool


class QualitySystemConfigResponse(BaseModel):
    positions: list[QualitySystemPosition] = Field(default_factory=list)
    file_categories: list[QualitySystemFileCategory] = Field(default_factory=list)


class QualitySystemUpdateAssignmentsRequest(BaseModel):
    user_ids: list[str] = Field(default_factory=list)
    change_reason: str


class QualitySystemCreateFileCategoryRequest(BaseModel):
    name: str
    change_reason: str


class QualitySystemDeactivateFileCategoryRequest(BaseModel):
    change_reason: str
