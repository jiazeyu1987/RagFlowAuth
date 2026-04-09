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
from .tree_builder import build_org_tree


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

    def get_employee_by_user_id(self, employee_user_id: str) -> Employee | None:
        return self._store.get_employee_by_user_id(employee_user_id)

    def list_audit_logs(
        self,
        *,
        entity_type: str | None = None,
        action: str | None = None,
        limit: int = 200,
    ):
        return self._store.list_audit_logs(entity_type=entity_type, action=action, limit=limit)

    def get_tree(self) -> list[dict]:
        return build_org_tree(
            companies=self.list_companies(),
            departments=self.list_departments_flat(),
            employees=self.list_employees(),
        )

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

    def _parse_excel(self, *, excel_path=None):
        parsed = self._parser.parse(excel_path=excel_path)
        return parsed.companies, parsed.departments, parsed.employees
