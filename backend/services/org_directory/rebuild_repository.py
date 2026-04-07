from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from backend.database.sqlite import connect_sqlite

from .models import Company, Department, Employee, OrgStructureRebuildSummary
from .rebuild_types import ParsedCompany, ParsedDepartment, ParsedEmployee, ParsedOrgStructure


@dataclass
class _RebuildStats:
    company_created: int = 0
    company_updated: int = 0
    company_deleted: int = 0
    department_created: int = 0
    department_updated: int = 0
    department_deleted: int = 0
    employee_created: int = 0
    employee_updated: int = 0
    employee_deleted: int = 0
    users_company_cleared: int = 0
    users_department_cleared: int = 0


class OrgStructureRebuildRepository:
    def __init__(self, *, db_path: str | Path):
        self._db_path = Path(db_path)

    def rebuild_from_parsed(
        self,
        *,
        actor_user_id: str,
        source_display: str,
        parsed: ParsedOrgStructure,
        completed_at_ms: int,
    ) -> OrgStructureRebuildSummary:
        stats = _RebuildStats()
        company_keys = {item.source_key for item in parsed.companies}
        department_keys = {item.source_key for item in parsed.departments}
        employee_keys = {item.source_key for item in parsed.employees}

        conn = connect_sqlite(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")

            existing_companies = self._load_existing_companies(conn)
            company_id_by_source_key = self._apply_companies(
                conn=conn,
                companies=parsed.companies,
                existing_companies=existing_companies,
                actor_user_id=actor_user_id,
                completed_at_ms=completed_at_ms,
                stats=stats,
            )

            existing_departments = self._load_existing_departments(conn)
            department_id_by_source_key = self._apply_departments(
                conn=conn,
                departments=parsed.departments,
                existing_departments=existing_departments,
                company_id_by_source_key=company_id_by_source_key,
                actor_user_id=actor_user_id,
                completed_at_ms=completed_at_ms,
                stats=stats,
            )

            existing_employees = self._load_existing_employees(conn)
            self._apply_employees(
                conn=conn,
                employees=parsed.employees,
                existing_employees=existing_employees,
                company_id_by_source_key=company_id_by_source_key,
                department_id_by_source_key=department_id_by_source_key,
                completed_at_ms=completed_at_ms,
                stats=stats,
            )

            self._delete_stale_employees(conn=conn, employee_keys=employee_keys, stats=stats)
            self._delete_stale_departments(
                conn=conn,
                department_keys=department_keys,
                actor_user_id=actor_user_id,
                stats=stats,
            )
            self._delete_stale_companies(
                conn=conn,
                company_keys=company_keys,
                actor_user_id=actor_user_id,
                stats=stats,
            )

            self._log(
                conn,
                entity_type="org_structure",
                action="rebuild",
                entity_id=None,
                before_name=source_display,
                after_name=self._build_summary_text(parsed=parsed, stats=stats),
                actor_user_id=actor_user_id,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return OrgStructureRebuildSummary(
            excel_path=source_display,
            company_count=len(parsed.companies),
            department_count=len(parsed.departments),
            employee_count=len(parsed.employees),
            companies_created=stats.company_created,
            companies_updated=stats.company_updated,
            companies_deleted=stats.company_deleted,
            departments_created=stats.department_created,
            departments_updated=stats.department_updated,
            departments_deleted=stats.department_deleted,
            employees_created=stats.employee_created,
            employees_updated=stats.employee_updated,
            employees_deleted=stats.employee_deleted,
            users_company_cleared=stats.users_company_cleared,
            users_department_cleared=stats.users_department_cleared,
            completed_at_ms=completed_at_ms,
        )

    def _apply_companies(
        self,
        *,
        conn,
        companies: list[ParsedCompany],
        existing_companies: dict[str, Company],
        actor_user_id: str,
        completed_at_ms: int,
        stats: _RebuildStats,
    ) -> dict[str, int]:
        company_id_by_source_key: dict[str, int] = {}
        for item in companies:
            current = existing_companies.get(item.source_key)
            if current is None:
                cur = conn.execute(
                    """
                    INSERT INTO companies (name, source_key, created_at_ms, updated_at_ms)
                    VALUES (?, ?, ?, ?)
                    """,
                    (item.name, item.source_key, completed_at_ms, completed_at_ms),
                )
                company_id = int(cur.lastrowid)
                stats.company_created += 1
                self._log(
                    conn,
                    entity_type="company",
                    action="create",
                    entity_id=company_id,
                    before_name=None,
                    after_name=item.name,
                    actor_user_id=actor_user_id,
                )
            else:
                company_id = current.company_id
                if current.name != item.name:
                    conn.execute(
                        """
                        UPDATE companies
                        SET name = ?, source_key = ?, updated_at_ms = ?
                        WHERE company_id = ?
                        """,
                        (item.name, item.source_key, completed_at_ms, company_id),
                    )
                    stats.company_updated += 1
                    self._log(
                        conn,
                        entity_type="company",
                        action="update",
                        entity_id=company_id,
                        before_name=current.name,
                        after_name=item.name,
                        actor_user_id=actor_user_id,
                    )
            company_id_by_source_key[item.source_key] = company_id
        return company_id_by_source_key

    def _apply_departments(
        self,
        *,
        conn,
        departments: list[ParsedDepartment],
        existing_departments: dict[str, Department],
        company_id_by_source_key: dict[str, int],
        actor_user_id: str,
        completed_at_ms: int,
        stats: _RebuildStats,
    ) -> dict[str, int]:
        department_id_by_source_key: dict[str, int] = {}
        for item in departments:
            company_id = company_id_by_source_key[item.company_source_key]
            parent_department_id = (
                department_id_by_source_key[item.parent_source_key] if item.parent_source_key is not None else None
            )
            current = existing_departments.get(item.source_key)
            if current is None:
                cur = conn.execute(
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
                        completed_at_ms,
                        completed_at_ms,
                    ),
                )
                department_id = int(cur.lastrowid)
                stats.department_created += 1
                self._log(
                    conn,
                    entity_type="department",
                    action="create",
                    entity_id=department_id,
                    before_name=None,
                    after_name=item.path_name,
                    actor_user_id=actor_user_id,
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
                    conn.execute(
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
                            completed_at_ms,
                            department_id,
                        ),
                    )
                    stats.department_updated += 1
                    self._log(
                        conn,
                        entity_type="department",
                        action="update",
                        entity_id=department_id,
                        before_name=current.path_name or current.name,
                        after_name=item.path_name,
                        actor_user_id=actor_user_id,
                    )
            department_id_by_source_key[item.source_key] = department_id
        return department_id_by_source_key

    def _apply_employees(
        self,
        *,
        conn,
        employees: list[ParsedEmployee],
        existing_employees: dict[str, Employee],
        company_id_by_source_key: dict[str, int],
        department_id_by_source_key: dict[str, int],
        completed_at_ms: int,
        stats: _RebuildStats,
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
                conn.execute(
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
                        completed_at_ms,
                        completed_at_ms,
                    ),
                )
                stats.employee_created += 1
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

            conn.execute(
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
                    completed_at_ms,
                    current.employee_id,
                ),
            )
            stats.employee_updated += 1

    def _delete_stale_employees(self, *, conn, employee_keys: set[str], stats: _RebuildStats) -> None:
        stale_employee_rows = [
            row
            for row in conn.execute(
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
        for batch in self._iter_chunks(stale_employee_ids, 500):
            conn.execute(
                "DELETE FROM org_employees WHERE employee_id IN ({placeholders})".format(
                    placeholders=self._placeholders(len(batch))
                ),
                tuple(batch),
            )
        stats.employee_deleted = len(stale_employee_ids)

    def _delete_stale_departments(
        self,
        *,
        conn,
        department_keys: set[str],
        actor_user_id: str,
        stats: _RebuildStats,
    ) -> None:
        stale_departments = self._select_stale_departments(conn, department_keys)
        stale_department_ids = [int(row["department_id"]) for row in stale_departments]
        if not stale_department_ids:
            return

        stats.users_department_cleared = conn.execute(
            """
            UPDATE users
            SET department_id = NULL
            WHERE department_id IN ({placeholders})
            """.format(placeholders=self._placeholders(len(stale_department_ids))),
            tuple(stale_department_ids),
        ).rowcount
        for row in stale_departments:
            self._log(
                conn,
                entity_type="department",
                action="delete",
                entity_id=int(row["department_id"]),
                before_name=str(row["path_name"] or row["name"] or ""),
                after_name=None,
                actor_user_id=actor_user_id,
            )
        conn.execute(
            "DELETE FROM departments WHERE department_id IN ({placeholders})".format(
                placeholders=self._placeholders(len(stale_department_ids))
            ),
            tuple(stale_department_ids),
        )
        stats.department_deleted = len(stale_department_ids)

    def _delete_stale_companies(
        self,
        *,
        conn,
        company_keys: set[str],
        actor_user_id: str,
        stats: _RebuildStats,
    ) -> None:
        stale_companies = self._select_stale_companies(conn, company_keys)
        stale_company_ids = [int(row["company_id"]) for row in stale_companies]
        if not stale_company_ids:
            return

        stats.users_company_cleared = conn.execute(
            """
            UPDATE users
            SET company_id = NULL
            WHERE company_id IN ({placeholders})
            """.format(placeholders=self._placeholders(len(stale_company_ids))),
            tuple(stale_company_ids),
        ).rowcount
        for row in stale_companies:
            self._log(
                conn,
                entity_type="company",
                action="delete",
                entity_id=int(row["company_id"]),
                before_name=str(row["name"] or ""),
                after_name=None,
                actor_user_id=actor_user_id,
            )
        conn.execute(
            "DELETE FROM companies WHERE company_id IN ({placeholders})".format(
                placeholders=self._placeholders(len(stale_company_ids))
            ),
            tuple(stale_company_ids),
        )
        stats.company_deleted = len(stale_company_ids)

    def _select_stale_departments(self, conn, department_keys: set[str]):
        if department_keys:
            return conn.execute(
                """
                SELECT
                    department_id,
                    name,
                    path_name
                FROM departments
                WHERE source_key NOT IN ({placeholders})
                ORDER BY level_no DESC, department_id DESC
                """.format(placeholders=self._placeholders(len(department_keys))),
                tuple(sorted(department_keys)),
            ).fetchall()
        return conn.execute(
            """
            SELECT department_id, name, path_name
            FROM departments
            ORDER BY level_no DESC, department_id DESC
            """
        ).fetchall()

    def _select_stale_companies(self, conn, company_keys: set[str]):
        if company_keys:
            return conn.execute(
                """
                SELECT company_id, name
                FROM companies
                WHERE source_key NOT IN ({placeholders})
                ORDER BY company_id DESC
                """.format(placeholders=self._placeholders(len(company_keys))),
                tuple(sorted(company_keys)),
            ).fetchall()
        return conn.execute(
            """
            SELECT company_id, name
            FROM companies
            ORDER BY company_id DESC
            """
        ).fetchall()

    @staticmethod
    def _load_existing_companies(conn) -> dict[str, Company]:
        return {
            row["source_key"]: Company(
                company_id=int(row["company_id"]),
                name=str(row["name"] or ""),
                source_key=str(row["source_key"] or ""),
                created_at_ms=int(row["created_at_ms"]),
                updated_at_ms=int(row["updated_at_ms"]),
            )
            for row in conn.execute(
                """
                SELECT company_id, name, source_key, created_at_ms, updated_at_ms
                FROM companies
                WHERE source_key IS NOT NULL
                """
            ).fetchall()
        }

    @staticmethod
    def _load_existing_departments(conn) -> dict[str, Department]:
        return {
            row["source_key"]: Department(
                department_id=int(row["department_id"]),
                name=str(row["name"] or ""),
                company_id=(int(row["company_id"]) if row["company_id"] is not None else None),
                parent_department_id=(
                    int(row["parent_department_id"]) if row["parent_department_id"] is not None else None
                ),
                source_key=str(row["source_key"] or ""),
                source_department_id=(
                    str(row["source_department_id"]).strip() if row["source_department_id"] is not None else None
                ),
                level_no=int(row["level_no"] or 0),
                path_name=str(row["path_name"] or ""),
                sort_order=int(row["sort_order"] or 0),
                created_at_ms=int(row["created_at_ms"]),
                updated_at_ms=int(row["updated_at_ms"]),
            )
            for row in conn.execute(
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
                """
            ).fetchall()
        }

    @staticmethod
    def _load_existing_employees(conn) -> dict[str, Employee]:
        return {
            row["source_key"]: Employee(
                employee_id=int(row["employee_id"]),
                employee_user_id=str(row["employee_user_id"] or ""),
                name=str(row["name"] or ""),
                email=(str(row["email"]).strip() if row["email"] is not None and str(row["email"]).strip() else None),
                employee_no=(
                    str(row["employee_no"]).strip()
                    if row["employee_no"] is not None and str(row["employee_no"]).strip()
                    else None
                ),
                department_manager_name=(
                    str(row["department_manager_name"]).strip()
                    if row["department_manager_name"] is not None and str(row["department_manager_name"]).strip()
                    else None
                ),
                is_department_manager=bool(int(row["is_department_manager"] or 0)),
                company_id=(int(row["company_id"]) if row["company_id"] is not None else None),
                department_id=(int(row["department_id"]) if row["department_id"] is not None else None),
                source_key=str(row["source_key"] or ""),
                sort_order=int(row["sort_order"] or 0),
                created_at_ms=int(row["created_at_ms"]),
                updated_at_ms=int(row["updated_at_ms"]),
            )
            for row in conn.execute(
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
                """
            ).fetchall()
        }

    @staticmethod
    def _build_summary_text(*, parsed: ParsedOrgStructure, stats: _RebuildStats) -> str:
        return (
            f"companies={len(parsed.companies)}, departments={len(parsed.departments)}, employees={len(parsed.employees)}, "
            f"company_changes=+{stats.company_created}/~{stats.company_updated}/-{stats.company_deleted}, "
            f"department_changes=+{stats.department_created}/~{stats.department_updated}/-{stats.department_deleted}, "
            f"employee_changes=+{stats.employee_created}/~{stats.employee_updated}/-{stats.employee_deleted}, "
            f"user_refs_cleared=company:{stats.users_company_cleared},department:{stats.users_department_cleared}"
        )

    @staticmethod
    def _log(
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
    def _placeholders(size: int) -> str:
        return ",".join("?" for _ in range(size))

    @staticmethod
    def _iter_chunks(values: list[int], size: int):
        for idx in range(0, len(values), size):
            yield values[idx : idx + size]
