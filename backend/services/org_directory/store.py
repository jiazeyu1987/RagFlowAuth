from __future__ import annotations

import time

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .models import Company, Department, Employee, OrgDirectoryAuditLog
from .rebuild_repository import OrgStructureRebuildRepository
from .rebuild_types import ParsedOrgStructure


class OrgDirectoryStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def list_companies(self) -> list[Company]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT company_id, name, source_key, created_at_ms, updated_at_ms
                FROM companies
                ORDER BY name COLLATE NOCASE ASC, company_id ASC
                """
            ).fetchall()
            return [self._row_to_company(row) for row in rows]
        finally:
            conn.close()

    def get_company(self, company_id: int) -> Company | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT company_id, name, source_key, created_at_ms, updated_at_ms
                FROM companies
                WHERE company_id = ?
                """,
                (company_id,),
            ).fetchone()
            return self._row_to_company(row) if row else None
        finally:
            conn.close()

    def list_departments(self) -> list[Department]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT
                    department_id,
                    name,
                    company_id,
                    parent_department_id,
                    source_key,
                    source_department_id,
                    level_no,
                    path_name,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                FROM departments
                ORDER BY
                    COALESCE(company_id, 0) ASC,
                    level_no ASC,
                    sort_order ASC,
                    path_name COLLATE NOCASE ASC,
                    department_id ASC
                """
            ).fetchall()
            return [self._row_to_department(row) for row in rows]
        finally:
            conn.close()

    def get_department(self, department_id: int) -> Department | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    department_id,
                    name,
                    company_id,
                    parent_department_id,
                    source_key,
                    source_department_id,
                    level_no,
                    path_name,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                FROM departments
                WHERE department_id = ?
                """,
                (department_id,),
            ).fetchone()
            return self._row_to_department(row) if row else None
        finally:
            conn.close()

    def list_employees(self) -> list[Employee]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT
                    employee_id,
                    employee_user_id,
                    name,
                    email,
                    employee_no,
                    department_manager_name,
                    is_department_manager,
                    company_id,
                    department_id,
                    source_key,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                FROM org_employees
                ORDER BY
                    COALESCE(company_id, 0) ASC,
                    CASE WHEN department_id IS NULL THEN 0 ELSE 1 END ASC,
                    COALESCE(department_id, 0) ASC,
                    is_department_manager DESC,
                    sort_order ASC,
                    name COLLATE NOCASE ASC,
                    employee_id ASC
                """
            ).fetchall()
            return [self._row_to_employee(row) for row in rows]
        finally:
            conn.close()

    def get_employee(self, employee_id: int) -> Employee | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    employee_id,
                    employee_user_id,
                    name,
                    email,
                    employee_no,
                    department_manager_name,
                    is_department_manager,
                    company_id,
                    department_id,
                    source_key,
                    sort_order,
                    created_at_ms,
                    updated_at_ms
                FROM org_employees
                WHERE employee_id = ?
                """,
                (employee_id,),
            ).fetchone()
            return self._row_to_employee(row) if row else None
        finally:
            conn.close()

    def list_audit_logs(
        self,
        *,
        entity_type: str | None = None,
        action: str | None = None,
        limit: int = 200,
    ) -> list[OrgDirectoryAuditLog]:
        limit = int(limit or 200)
        limit = max(1, min(limit, 1000))

        entity_type = (entity_type or "").strip() or None
        action = (action or "").strip() or None

        conn = self._get_connection()
        try:
            query = """
                SELECT id, entity_type, action, entity_id, before_name, after_name, actor_user_id, created_at_ms
                FROM org_directory_audit_logs
                WHERE 1=1
            """
            params: list[object] = []
            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)
            if action:
                query += " AND action = ?"
                params.append(action)
            query += " ORDER BY created_at_ms DESC, id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [OrgDirectoryAuditLog(*row) for row in rows]
        finally:
            conn.close()

    def rebuild_from_parsed(
        self,
        *,
        actor_user_id: str,
        source_display: str,
        parsed: ParsedOrgStructure,
        completed_at_ms: int,
    ):
        repository = OrgStructureRebuildRepository(db_path=self.db_path)
        return repository.rebuild_from_parsed(
            actor_user_id=actor_user_id,
            source_display=source_display,
            parsed=parsed,
            completed_at_ms=completed_at_ms,
        )

    def _log(
        self,
        conn,
        *,
        entity_type: str,
        action: str,
        entity_id: int | None,
        before_name: str | None,
        after_name: str | None,
        actor_user_id: str,
    ) -> None:
        now_ms = int(time.time() * 1000)
        conn.execute(
            """
            INSERT INTO org_directory_audit_logs (
                entity_type, action, entity_id, before_name, after_name, actor_user_id, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (entity_type, action, entity_id, before_name, after_name, actor_user_id, now_ms),
        )

    @staticmethod
    def _row_to_company(row) -> Company:
        return Company(
            company_id=int(row[0]),
            name=str(row[1] or ""),
            source_key=(str(row[2]).strip() if row[2] is not None else None),
            created_at_ms=int(row[3]),
            updated_at_ms=int(row[4]),
        )

    @staticmethod
    def _row_to_department(row) -> Department:
        return Department(
            department_id=int(row[0]),
            name=str(row[1] or ""),
            company_id=(int(row[2]) if row[2] is not None else None),
            parent_department_id=(int(row[3]) if row[3] is not None else None),
            source_key=(str(row[4]).strip() if row[4] is not None else None),
            source_department_id=(str(row[5]).strip() if row[5] is not None else None),
            level_no=int(row[6] or 0),
            path_name=str(row[7] or ""),
            sort_order=int(row[8] or 0),
            created_at_ms=int(row[9]),
            updated_at_ms=int(row[10]),
        )

    @staticmethod
    def _row_to_employee(row) -> Employee:
        return Employee(
            employee_id=int(row[0]),
            employee_user_id=str(row[1] or ""),
            name=str(row[2] or ""),
            email=(str(row[3]).strip() if row[3] is not None and str(row[3]).strip() else None),
            employee_no=(str(row[4]).strip() if row[4] is not None and str(row[4]).strip() else None),
            department_manager_name=(str(row[5]).strip() if row[5] is not None and str(row[5]).strip() else None),
            is_department_manager=bool(int(row[6] or 0)),
            company_id=(int(row[7]) if row[7] is not None else None),
            department_id=(int(row[8]) if row[8] is not None else None),
            source_key=str(row[9] or ""),
            sort_order=int(row[10] or 0),
            created_at_ms=int(row[11]),
            updated_at_ms=int(row[12]),
        )
