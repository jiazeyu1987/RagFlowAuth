from __future__ import annotations

from dataclasses import dataclass
import time

from .models import Company, Department, Employee, OrgStructureRebuildSummary
from .rebuild_types import ParsedOrgStructure


@dataclass
class RebuildStats:
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


def build_rebuild_summary(
    *,
    source_display: str,
    parsed: ParsedOrgStructure,
    completed_at_ms: int,
    stats: RebuildStats,
) -> OrgStructureRebuildSummary:
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


def build_summary_text(*, parsed: ParsedOrgStructure, stats: RebuildStats) -> str:
    return (
        f"companies={len(parsed.companies)}"
        f",departments={len(parsed.departments)}"
        f",employees={len(parsed.employees)}"
        f",company_changes={stats.company_created + stats.company_updated + stats.company_deleted}"
        f",department_changes={stats.department_created + stats.department_updated + stats.department_deleted}"
        f",employee_changes={stats.employee_created + stats.employee_updated + stats.employee_deleted}"
    )


def load_existing_companies(conn) -> dict[str, Company]:
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


def load_existing_departments(conn) -> dict[str, Department]:
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


def load_existing_employees(conn) -> dict[str, Employee]:
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
            WHERE source_key IS NOT NULL
            """
        ).fetchall()
    }


def select_stale_departments(conn, department_keys: set[str]):
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
            """.format(placeholders=placeholders(len(department_keys))),
            tuple(sorted(department_keys)),
        ).fetchall()
    return conn.execute(
        """
        SELECT department_id, name, path_name
        FROM departments
        ORDER BY level_no DESC, department_id DESC
        """
    ).fetchall()


def select_stale_companies(conn, company_keys: set[str]):
    if company_keys:
        return conn.execute(
            """
            SELECT company_id, name
            FROM companies
            WHERE source_key NOT IN ({placeholders})
            ORDER BY company_id DESC
            """.format(placeholders=placeholders(len(company_keys))),
            tuple(sorted(company_keys)),
        ).fetchall()
    return conn.execute(
        """
        SELECT company_id, name
        FROM companies
        ORDER BY company_id DESC
        """
    ).fetchall()


def log_rebuild_event(
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


def iter_chunks(items: list[int], size: int):
    if size <= 0:
        raise RuntimeError("org_directory_chunk_size_invalid")
    for index in range(0, len(items), size):
        yield items[index : index + size]


def placeholders(count: int) -> str:
    if count <= 0:
        raise RuntimeError("org_directory_placeholder_count_invalid")
    return ",".join(["?"] * count)
