from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCompany:
    name: str
    source_key: str


@dataclass(frozen=True)
class ParsedDepartment:
    name: str
    company_source_key: str
    parent_source_key: str | None
    source_key: str
    source_department_id: str | None
    level_no: int
    path_name: str
    sort_order: int


@dataclass(frozen=True)
class ParsedEmployee:
    employee_user_id: str
    name: str
    email: str | None
    employee_no: str | None
    department_manager_name: str | None
    is_department_manager: bool
    company_source_key: str
    department_source_key: str | None
    source_key: str
    path_name: str
    sort_order: int


@dataclass(frozen=True)
class ParsedOrgStructure:
    companies: list[ParsedCompany]
    departments: list[ParsedDepartment]
    employees: list[ParsedEmployee]

    def __iter__(self):
        yield self.companies
        yield self.departments
        yield self.employees
