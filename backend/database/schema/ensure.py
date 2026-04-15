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
from .chat_management import ensure_chat_ownerships_table
from .chat_message_sources import ensure_chat_message_sources_table
from .search_configs import ensure_search_configs_table
from .upload_settings import ensure_upload_settings_table
from .config_change_logs import ensure_config_change_logs_table
from .quality_system_config import ensure_quality_system_config_tables
from .kb_directory import ensure_kb_directory_tables
from .data_security import (
    add_cron_schedule_columns_to_data_security,
    add_backup_verification_columns_to_backup_jobs,
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
from .restore_drills import ensure_restore_drills_table
from .kb_documents import ensure_kb_documents_table
from .document_control import ensure_document_control_tables
from .patent_downloads import ensure_patent_download_tables
from .paper_downloads import ensure_paper_download_tables
from .package_drawings import ensure_package_drawing_tables
from .org_directory import (
    ensure_companies_table,
    ensure_departments_table,
    ensure_org_employees_table,
    ensure_org_directory_audit_logs_table,
)
from .permission_groups import (
    backfill_user_permission_groups_from_users_group_id,
    ensure_user_tool_permissions_table,
    ensure_permission_groups_table,
    ensure_user_permission_groups_table,
    migrate_user_tools_from_permission_groups,
    seed_default_permission_groups,
)
from .auth_sessions import ensure_auth_login_sessions_table
from .approval_workflow import ensure_approval_workflow_tables
from .electronic_signatures import ensure_electronic_signature_tables
from .emergency_changes import ensure_emergency_change_tables
from .change_control import ensure_change_control_tables
from .equipment import ensure_equipment_tables
from .maintenance import ensure_maintenance_tables
from .metrology import ensure_metrology_tables
from .notification import ensure_notification_tables
from .supplier_qualification import ensure_supplier_qualification_tables
from .training_compliance import ensure_training_compliance_tables
from .training_ack import ensure_training_ack_tables
from .governance_closure import ensure_governance_closure_tables
from .batch_records import ensure_batch_records_tables
from .watermark_policy import ensure_watermark_policy_tables
from .operation_approval import (
    ensure_operation_approval_tables,
    ensure_user_inbox_tables,
    repair_operation_approval_notification_mojibake,
)
from .permission_group_folders import (
    ensure_permission_group_folders_table,
    ensure_permission_groups_folder_column,
)
from .users import (
    ensure_password_history_table,
    ensure_org_columns_on_users,
    ensure_user_employee_user_id_column,
    ensure_user_full_name_column,
    ensure_user_electronic_signature_columns,
    ensure_user_login_policy_columns,
    ensure_user_managed_kb_root_column,
    ensure_user_password_security_columns,
    ensure_users_group_id_column,
    ensure_users_table,
)


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
        ensure_user_login_policy_columns(conn)
        ensure_user_full_name_column(conn)
        ensure_user_managed_kb_root_column(conn)
        ensure_user_electronic_signature_columns(conn)
        ensure_user_password_security_columns(conn)
        ensure_password_history_table(conn)
        ensure_auth_login_sessions_table(conn)
        ensure_kb_documents_table(conn)
        ensure_document_control_tables(conn)
        ensure_chat_sessions_table(conn)
        ensure_chat_ownerships_table(conn)
        ensure_chat_message_sources_table(conn)
        ensure_search_configs_table(conn)
        ensure_upload_settings_table(conn)
        ensure_config_change_logs_table(conn)
        ensure_quality_system_config_tables(conn)
        ensure_kb_directory_tables(conn)
        ensure_patent_download_tables(conn)
        ensure_paper_download_tables(conn)
        ensure_package_drawing_tables(conn)

        # Permission groups (authorization model)
        ensure_permission_groups_table(conn)
        ensure_permission_group_folders_table(conn)
        ensure_permission_groups_folder_column(conn)
        ensure_user_permission_groups_table(conn)
        ensure_user_tool_permissions_table(conn)
        ensure_users_group_id_column(conn)
        seed_default_permission_groups(conn)
        backfill_user_permission_groups_from_users_group_id(conn)
        migrate_user_tools_from_permission_groups(conn)

        # Data security / backup
        ensure_data_security_settings_table(conn)
        ensure_backup_jobs_table(conn)
        ensure_backup_locks_table(conn)
        add_backup_job_kind_column(conn)
        add_cancel_columns_to_backup_jobs(conn)
        add_backup_verification_columns_to_backup_jobs(conn)
        add_full_backup_columns_to_data_security(conn)
        add_backup_retention_columns_to_data_security(conn)
        add_cron_schedule_columns_to_data_security(conn)
        add_last_backup_time_columns_to_data_security(conn)
        add_replica_columns_to_data_security(conn)
        ensure_restore_drills_table(conn)

        # Org directory (companies/departments) + audit
        ensure_companies_table(conn)
        ensure_departments_table(conn)
        ensure_org_employees_table(conn)
        ensure_org_directory_audit_logs_table(conn)
        ensure_org_columns_on_users(conn)
        ensure_user_employee_user_id_column(conn)

        # Audit tables
        ensure_download_logs_table(conn)
        ensure_deletion_logs_table(conn)
        ensure_audit_events_table(conn)
        ensure_approval_workflow_tables(conn)
        ensure_electronic_signature_tables(conn)
        ensure_emergency_change_tables(conn)
        ensure_change_control_tables(conn)
        ensure_equipment_tables(conn)
        ensure_metrology_tables(conn)
        ensure_maintenance_tables(conn)
        ensure_notification_tables(conn)
        ensure_operation_approval_tables(conn)
        ensure_user_inbox_tables(conn)
        repair_operation_approval_notification_mojibake(conn)
        ensure_supplier_qualification_tables(conn)
        ensure_training_compliance_tables(conn)
        ensure_training_ack_tables(conn)
        ensure_governance_closure_tables(conn)
        ensure_batch_records_tables(conn)
        ensure_watermark_policy_tables(conn)

        # Cross-table KB reference columns & indexes
        ensure_kb_ref_columns(conn)
        ensure_deletion_log_extended_columns(conn)
        ensure_kb_ref_indexes(conn)

        conn.commit()
    finally:
        conn.close()
