from __future__ import annotations

from pathlib import Path

from backend.database.sqlite import connect_sqlite

from .rebuild_mutator import OrgStructureRebuildMutator
from .rebuild_support import (
    RebuildStats,
    build_rebuild_summary,
    build_summary_text,
    load_existing_companies,
    load_existing_departments,
    load_existing_employees,
    log_rebuild_event,
)
from .rebuild_types import ParsedOrgStructure


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
    ):
        stats = RebuildStats()
        company_keys = {item.source_key for item in parsed.companies}
        department_keys = {item.source_key for item in parsed.departments}
        employee_keys = {item.source_key for item in parsed.employees}

        conn = connect_sqlite(self._db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            mutator = OrgStructureRebuildMutator(
                conn=conn,
                actor_user_id=actor_user_id,
                completed_at_ms=completed_at_ms,
                stats=stats,
            )

            company_id_by_source_key = mutator.apply_companies(
                companies=parsed.companies,
                existing_companies=load_existing_companies(conn),
            )
            department_id_by_source_key = mutator.apply_departments(
                departments=parsed.departments,
                existing_departments=load_existing_departments(conn),
                company_id_by_source_key=company_id_by_source_key,
            )
            mutator.apply_employees(
                employees=parsed.employees,
                existing_employees=load_existing_employees(conn),
                company_id_by_source_key=company_id_by_source_key,
                department_id_by_source_key=department_id_by_source_key,
            )

            mutator.delete_stale_employees(employee_keys=employee_keys)
            mutator.delete_stale_departments(department_keys=department_keys)
            mutator.delete_stale_companies(company_keys=company_keys)

            log_rebuild_event(
                conn,
                entity_type="org_structure",
                action="rebuild",
                entity_id=None,
                before_name=source_display,
                after_name=build_summary_text(parsed=parsed, stats=stats),
                actor_user_id=actor_user_id,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return build_rebuild_summary(
            source_display=source_display,
            parsed=parsed,
            completed_at_ms=completed_at_ms,
            stats=stats,
        )
