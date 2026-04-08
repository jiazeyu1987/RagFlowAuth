from __future__ import annotations

from .models import Company, Department, Employee
from .rebuild_support import (
    RebuildStats,
    iter_chunks,
    log_rebuild_event,
    placeholders,
    select_stale_companies,
    select_stale_departments,
)
from .rebuild_types import ParsedCompany, ParsedDepartment, ParsedEmployee


class OrgStructureRebuildMutator:
    def __init__(
        self,
        *,
        conn,
        actor_user_id: str,
        completed_at_ms: int,
        stats: RebuildStats,
    ) -> None:
        self._conn = conn
        self._actor_user_id = actor_user_id
        self._completed_at_ms = completed_at_ms
        self._stats = stats

    def apply_companies(
        self,
        *,
        companies: list[ParsedCompany],
        existing_companies: dict[str, Company],
    ) -> dict[str, int]:
        company_id_by_source_key: dict[str, int] = {}
        for item in companies:
            current = existing_companies.get(item.source_key)
            if current is None:
                cur = self._conn.execute(
                    """
                    INSERT INTO companies (name, source_key, created_at_ms, updated_at_ms)
                    VALUES (?, ?, ?, ?)
                    """,
                    (item.name, item.source_key, self._completed_at_ms, self._completed_at_ms),
                )
                company_id = int(cur.lastrowid)
                self._stats.company_created += 1
                log_rebuild_event(
                    self._conn,
                    entity_type="company",
                    action="create",
                    entity_id=company_id,
                    before_name=None,
                    after_name=item.name,
                    actor_user_id=self._actor_user_id,
                )
            else:
                company_id = current.company_id
                if current.name != item.name:
                    self._conn.execute(
                        """
                        UPDATE companies
                        SET name = ?, source_key = ?, updated_at_ms = ?
                        WHERE company_id = ?
                        """,
                        (item.name, item.source_key, self._completed_at_ms, company_id),
                    )
                    self._stats.company_updated += 1
                    log_rebuild_event(
                        self._conn,
                        entity_type="company",
                        action="update",
                        entity_id=company_id,
                        before_name=current.name,
                        after_name=item.name,
                        actor_user_id=self._actor_user_id,
                    )
            company_id_by_source_key[item.source_key] = company_id
        return company_id_by_source_key

    def apply_departments(
        self,
        *,
        departments: list[ParsedDepartment],
        existing_departments: dict[str, Department],
        company_id_by_source_key: dict[str, int],
    ) -> dict[str, int]:
        department_id_by_source_key: dict[str, int] = {}
        for item in departments:
            company_id = company_id_by_source_key[item.company_source_key]
            parent_department_id = (
                department_id_by_source_key[item.parent_source_key] if item.parent_source_key is not None else None
            )
            current = existing_departments.get(item.source_key)
            if current is None:
                cur = self._conn.execute(
                    """
                    INSERT INTO departments (
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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.name,
                        company_id,
                        parent_department_id,
                        item.source_key,
                        item.source_department_id,
                        item.level_no,
                        item.path_name,
                        item.sort_order,
                        self._completed_at_ms,
                        self._completed_at_ms,
                    ),
                )
                department_id = int(cur.lastrowid)
                self._stats.department_created += 1
                log_rebuild_event(
                    self._conn,
                    entity_type="department",
                    action="create",
                    entity_id=department_id,
                    before_name=None,
                    after_name=item.path_name,
                    actor_user_id=self._actor_user_id,
                )
            else:
                department_id = current.department_id
                needs_update = (
                    current.name != item.name
                    or current.company_id != company_id
                    or current.parent_department_id != parent_department_id
                    or current.source_department_id != item.source_department_id
                    or current.level_no != item.level_no
                    or current.path_name != item.path_name
                    or current.sort_order != item.sort_order
                )
                if needs_update:
                    self._conn.execute(
                        """
                        UPDATE departments
                        SET
                            name = ?,
                            company_id = ?,
                            parent_department_id = ?,
                            source_key = ?,
                            source_department_id = ?,
                            level_no = ?,
                            path_name = ?,
                            sort_order = ?,
                            updated_at_ms = ?
                        WHERE department_id = ?
                        """,
                        (
                            item.name,
                            company_id,
                            parent_department_id,
                            item.source_key,
                            item.source_department_id,
                            item.level_no,
                            item.path_name,
                            item.sort_order,
                            self._completed_at_ms,
                            department_id,
                        ),
                    )
                    self._stats.department_updated += 1
                    log_rebuild_event(
                        self._conn,
                        entity_type="department",
                        action="update",
                        entity_id=department_id,
                        before_name=current.path_name or current.name,
                        after_name=item.path_name,
                        actor_user_id=self._actor_user_id,
                    )
            department_id_by_source_key[item.source_key] = department_id
        return department_id_by_source_key

    def apply_employees(
        self,
        *,
        employees: list[ParsedEmployee],
        existing_employees: dict[str, Employee],
        company_id_by_source_key: dict[str, int],
        department_id_by_source_key: dict[str, int],
    ) -> None:
        for item in employees:
            company_id = company_id_by_source_key[item.company_source_key]
            department_id = (
                department_id_by_source_key[item.department_source_key]
                if item.department_source_key is not None
                else None
            )
            current = existing_employees.get(item.source_key)
            if current is None:
                self._conn.execute(
                    """
                    INSERT INTO org_employees (
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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.employee_user_id,
                        item.name,
                        item.email,
                        item.employee_no,
                        item.department_manager_name,
                        1 if item.is_department_manager else 0,
                        company_id,
                        department_id,
                        item.source_key,
                        item.sort_order,
                        self._completed_at_ms,
                        self._completed_at_ms,
                    ),
                )
                self._stats.employee_created += 1
                continue

            needs_update = (
                current.employee_user_id != item.employee_user_id
                or current.name != item.name
                or current.email != item.email
                or current.employee_no != item.employee_no
                or current.department_manager_name != item.department_manager_name
                or current.is_department_manager != item.is_department_manager
                or current.company_id != company_id
                or current.department_id != department_id
                or current.sort_order != item.sort_order
            )
            if not needs_update:
                continue

            self._conn.execute(
                """
                UPDATE org_employees
                SET
                    employee_user_id = ?,
                    name = ?,
                    email = ?,
                    employee_no = ?,
                    department_manager_name = ?,
                    is_department_manager = ?,
                    company_id = ?,
                    department_id = ?,
                    source_key = ?,
                    sort_order = ?,
                    updated_at_ms = ?
                WHERE employee_id = ?
                """,
                (
                    item.employee_user_id,
                    item.name,
                    item.email,
                    item.employee_no,
                    item.department_manager_name,
                    1 if item.is_department_manager else 0,
                    company_id,
                    department_id,
                    item.source_key,
                    item.sort_order,
                    self._completed_at_ms,
                    current.employee_id,
                ),
            )
            self._stats.employee_updated += 1

    def delete_stale_employees(self, *, employee_keys: set[str]) -> None:
        stale_employee_rows = [
            row
            for row in self._conn.execute(
                """
                SELECT employee_id, source_key
                FROM org_employees
                """
            ).fetchall()
            if str(row["source_key"] or "") not in employee_keys
        ]
        stale_employee_ids = [int(row["employee_id"]) for row in stale_employee_rows]
        if not stale_employee_ids:
            return
        for batch in iter_chunks(stale_employee_ids, 500):
            self._conn.execute(
                "DELETE FROM org_employees WHERE employee_id IN ({placeholders})".format(
                    placeholders=placeholders(len(batch))
                ),
                tuple(batch),
            )
        self._stats.employee_deleted = len(stale_employee_ids)

    def delete_stale_departments(self, *, department_keys: set[str]) -> None:
        stale_departments = select_stale_departments(self._conn, department_keys)
        stale_department_ids = [int(row["department_id"]) for row in stale_departments]
        if not stale_department_ids:
            return

        self._stats.users_department_cleared = self._conn.execute(
            """
            UPDATE users
            SET department_id = NULL
            WHERE department_id IN ({placeholders})
            """.format(placeholders=placeholders(len(stale_department_ids))),
            tuple(stale_department_ids),
        ).rowcount
        for row in stale_departments:
            log_rebuild_event(
                self._conn,
                entity_type="department",
                action="delete",
                entity_id=int(row["department_id"]),
                before_name=str(row["path_name"] or row["name"] or ""),
                after_name=None,
                actor_user_id=self._actor_user_id,
            )
        self._conn.execute(
            "DELETE FROM departments WHERE department_id IN ({placeholders})".format(
                placeholders=placeholders(len(stale_department_ids))
            ),
            tuple(stale_department_ids),
        )
        self._stats.department_deleted = len(stale_department_ids)

    def delete_stale_companies(self, *, company_keys: set[str]) -> None:
        stale_companies = select_stale_companies(self._conn, company_keys)
        stale_company_ids = [int(row["company_id"]) for row in stale_companies]
        if not stale_company_ids:
            return

        self._stats.users_company_cleared = self._conn.execute(
            """
            UPDATE users
            SET company_id = NULL
            WHERE company_id IN ({placeholders})
            """.format(placeholders=placeholders(len(stale_company_ids))),
            tuple(stale_company_ids),
        ).rowcount
        for row in stale_companies:
            log_rebuild_event(
                self._conn,
                entity_type="company",
                action="delete",
                entity_id=int(row["company_id"]),
                before_name=str(row["name"] or ""),
                after_name=None,
                actor_user_id=self._actor_user_id,
            )
        self._conn.execute(
            "DELETE FROM companies WHERE company_id IN ({placeholders})".format(
                placeholders=placeholders(len(stale_company_ids))
            ),
            tuple(stale_company_ids),
        )
        self._stats.company_deleted = len(stale_company_ids)
