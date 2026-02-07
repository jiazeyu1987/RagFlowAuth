from __future__ import annotations

from pathlib import Path

from backend.database.sqlite import connect_sqlite

from .audit_logs import (
    ensure_deletion_log_extended_columns,
    ensure_deletion_logs_table,
    ensure_download_logs_table,
    ensure_audit_events_table,
    ensure_kb_ref_columns,
    ensure_kb_ref_indexes,
)
from .chat_sessions import ensure_chat_sessions_table
from .chat_message_sources import ensure_chat_message_sources_table
from .data_security import (
    add_cron_schedule_columns_to_data_security,
    add_backup_job_kind_column,
    add_cancel_columns_to_backup_jobs,
    add_full_backup_columns_to_data_security,
    add_backup_retention_columns_to_data_security,
    add_last_backup_time_columns_to_data_security,
    add_replica_columns_to_data_security,
    ensure_backup_jobs_table,
    ensure_backup_locks_table,
    ensure_data_security_settings_table,
)
from .kb_documents import ensure_kb_documents_table
from .org_directory import (
    ensure_companies_table,
    ensure_departments_table,
    ensure_org_directory_audit_logs_table,
    seed_default_companies,
    seed_default_departments,
)
from .permission_groups import (
    backfill_user_permission_groups_from_users_group_id,
    ensure_permission_groups_table,
    ensure_user_permission_groups_table,
    seed_default_permission_groups,
)
from .users import ensure_org_columns_on_users, ensure_users_group_id_column, ensure_users_table


def ensure_schema(db_path: str | Path) -> None:
    """
    Ensure baseline schema exists and apply additive schema changes.

    Safe to call repeatedly; no-op when schema already exists.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect_sqlite(db_path)
    try:
        # Core tables
        ensure_users_table(conn)
        ensure_kb_documents_table(conn)
        ensure_chat_sessions_table(conn)
        ensure_chat_message_sources_table(conn)

        # Permission groups (authorization model)
        ensure_permission_groups_table(conn)
        ensure_user_permission_groups_table(conn)
        ensure_users_group_id_column(conn)
        seed_default_permission_groups(conn)
        backfill_user_permission_groups_from_users_group_id(conn)

        # Data security / backup
        ensure_data_security_settings_table(conn)
        ensure_backup_jobs_table(conn)
        ensure_backup_locks_table(conn)
        add_backup_job_kind_column(conn)
        add_cancel_columns_to_backup_jobs(conn)
        add_full_backup_columns_to_data_security(conn)
        add_backup_retention_columns_to_data_security(conn)
        add_cron_schedule_columns_to_data_security(conn)
        add_last_backup_time_columns_to_data_security(conn)
        add_replica_columns_to_data_security(conn)

        # Org directory (companies/departments) + audit
        ensure_companies_table(conn)
        ensure_departments_table(conn)
        ensure_org_directory_audit_logs_table(conn)
        seed_default_companies(conn)
        seed_default_departments(conn)
        ensure_org_columns_on_users(conn)

        # Audit tables
        ensure_download_logs_table(conn)
        ensure_deletion_logs_table(conn)
        ensure_audit_events_table(conn)

        # Cross-table KB reference columns & indexes
        ensure_kb_ref_columns(conn)
        ensure_deletion_log_extended_columns(conn)
        ensure_kb_ref_indexes(conn)

        conn.commit()
    finally:
        conn.close()
