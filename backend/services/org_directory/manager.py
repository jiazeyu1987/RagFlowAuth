from __future__ import annotations

import time

from .excel_parser import (
    DEPARTMENT_LEVEL_HEADERS,
    EXCEL_RELATIVE_PATH,
    HEADER_COMPANY,
    HEADER_DEPARTMENT_MANAGER,
    HEADER_EMPLOYEE_EMAIL,
    HEADER_EMPLOYEE_NAME,
    HEADER_EMPLOYEE_NO,
    HEADER_EMPLOYEE_USER_ID,
    HEADER_SOURCE_DEPARTMENT_ID,
    OrgStructureExcelParser,
)
from .models import Company, Department, Employee, OrgStructureRebuildSummary
from .store import OrgDirectoryStore


class OrgStructureManager:
    def __init__(
        self,
        *,
        store: OrgDirectoryStore,
        excel_path=None,
        parser: OrgStructureExcelParser | None = None,
    ):
        if store is None:
            raise RuntimeError("org_directory_store_unavailable")
        self._store = store
        self._parser = parser or OrgStructureExcelParser(excel_path=excel_path or EXCEL_RELATIVE_PATH)

    @property
    def excel_path(self):
        return self._parser.excel_path

    def list_companies(self) -> list[Company]:
        return self._store.list_companies()

    def list_departments_flat(self) -> list[Department]:
        return self._store.list_departments()

    def list_employees(self) -> list[Employee]:
        return self._store.list_employees()

    def get_company(self, company_id: int) -> Company | None:
        return self._store.get_company(company_id)

    def get_department(self, department_id: int) -> Department | None:
        return self._store.get_department(department_id)

    def get_employee(self, employee_id: int) -> Employee | None:
        return self._store.get_employee(employee_id)

    def list_audit_logs(
        self,
        *,
        entity_type: str | None = None,
        action: str | None = None,
        limit: int = 200,
    ):
        return self._store.list_audit_logs(entity_type=entity_type, action=action, limit=limit)

    def get_tree(self) -> list[dict]:
        companies = self.list_companies()
        departments = self.list_departments_flat()
        employees = self.list_employees()

        company_by_id = {item.company_id: item for item in companies}
        department_by_id = {item.department_id: item for item in departments}
        children_by_parent: dict[int, list[dict]] = {}
        roots_by_company: dict[int, list[dict]] = {}
        people_by_department: dict[int, list[dict]] = {}
        people_by_company: dict[int, list[dict]] = {}

        for department in departments:
            node = self._department_node(department)
            if department.parent_department_id is None:
                roots_by_company.setdefault(int(department.company_id or 0), []).append(node)
            else:
                children_by_parent.setdefault(department.parent_department_id, []).append(node)

        for employee in employees:
            company = company_by_id.get(int(employee.company_id or 0))
            if company is None:
                raise RuntimeError(f"org_employee_company_missing:{employee.employee_user_id}")
            department = None
            if employee.department_id is not None:
                department = department_by_id.get(employee.department_id)
                if department is None:
                    raise RuntimeError(f"org_employee_department_missing:{employee.employee_user_id}")
            node = self._employee_node(employee, company=company, department=department)
            if employee.department_id is None:
                people_by_company.setdefault(company.company_id, []).append(node)
            else:
                people_by_department.setdefault(employee.department_id, []).append(node)

        def attach_children(nodes: list[dict]) -> list[dict]:
            attached: list[dict] = []
            for node in nodes:
                child_nodes = children_by_parent.get(node["id"], [])
                node["children"] = attach_children(child_nodes) + people_by_department.get(node["id"], [])
                attached.append(node)
            return attached

        tree: list[dict] = []
        for company in companies:
            root_children = roots_by_company.get(company.company_id, [])
            tree.append(
                {
                    "id": company.company_id,
                    "node_type": "company",
                    "name": company.name,
                    "path_name": company.name,
                    "source_key": company.source_key,
                    "company_id": company.company_id,
                    "department_id": None,
                    "parent_department_id": None,
                    "level_no": 1,
                    "source_department_id": None,
                    "employee_user_id": None,
                    "email": None,
                    "employee_no": None,
                    "department_manager_name": None,
                    "is_department_manager": False,
                    "created_at_ms": company.created_at_ms,
                    "updated_at_ms": company.updated_at_ms,
                    "children": attach_children(root_children) + people_by_company.get(company.company_id, []),
                }
            )
        return tree

    def rebuild_from_excel(
        self,
        *,
        actor_user_id: str,
        excel_path=None,
        source_label: str | None = None,
    ) -> OrgStructureRebuildSummary:
        actor = str(actor_user_id or "").strip()
        if not actor:
            raise RuntimeError("actor_user_id_required")
        resolved_excel_path = self._parser.resolve_excel_path(excel_path)
        source_display = str(source_label or resolved_excel_path)
        parsed = self._parser.parse(excel_path=resolved_excel_path)
        completed_at_ms = int(time.time() * 1000)
        return self._store.rebuild_from_parsed(
            actor_user_id=actor,
            source_display=source_display,
            parsed=parsed,
            completed_at_ms=completed_at_ms,
        )

    def _department_node(self, department: Department) -> dict:
        return {
            "id": department.department_id,
            "node_type": "department",
            "name": department.name,
            "path_name": department.path_name,
            "source_key": department.source_key,
            "company_id": department.company_id,
            "department_id": department.department_id,
            "parent_department_id": department.parent_department_id,
            "level_no": department.level_no,
            "source_department_id": department.source_department_id,
            "employee_user_id": None,
            "email": None,
            "employee_no": None,
            "department_manager_name": None,
            "is_department_manager": False,
            "created_at_ms": department.created_at_ms,
            "updated_at_ms": department.updated_at_ms,
            "children": [],
        }

    def _employee_node(self, employee: Employee, *, company: Company, department: Department | None) -> dict:
        parent_path = department.path_name if department is not None else company.name
        return {
            "id": employee.employee_id,
            "node_type": "person",
            "name": employee.name,
            "path_name": f"{parent_path} / {employee.name}",
            "source_key": employee.source_key,
            "company_id": employee.company_id,
            "department_id": employee.department_id,
            "parent_department_id": employee.department_id,
            "level_no": (department.level_no + 1) if department is not None else 2,
            "source_department_id": None,
            "employee_user_id": employee.employee_user_id,
            "email": employee.email,
            "employee_no": employee.employee_no,
            "department_manager_name": employee.department_manager_name,
            "is_department_manager": employee.is_department_manager,
            "created_at_ms": employee.created_at_ms,
            "updated_at_ms": employee.updated_at_ms,
            "children": [],
        }

    def _parse_excel(self, *, excel_path=None):
        parsed = self._parser.parse(excel_path=excel_path)
        return parsed.companies, parsed.departments, parsed.employees
