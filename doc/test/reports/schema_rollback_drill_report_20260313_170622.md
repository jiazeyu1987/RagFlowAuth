# IT-MIGRATION-ROLLBACK-001 Rollback Drill Report

- Generated at: 2026-03-13 17:06:22
- Drill database: `C:\Users\BJB110\AppData\Local\Temp\ragflowauth_schema_rollback_e331971368d04a64a909e1548149527b\auth.db`
- Scopes: full
- Overall verdict: **PASS**

## Scope: full

- Verdict: **PASS**
- Target tables: 33
- Checks: before_ok=True rollback_ok=True recover_ok=True

| Table | Before | AfterRollback | AfterRecover |
|---|---|---|---|
| chat_message_sources | True | False | True |
| chat_sessions | True | False | True |
| auth_login_sessions | True | False | True |
| user_permission_groups | True | False | True |
| permission_group_folders | True | False | True |
| permission_groups | True | False | True |
| paper_download_items | True | False | True |
| paper_download_sessions | True | False | True |
| patent_download_items | True | False | True |
| patent_download_sessions | True | False | True |
| kb_directory_dataset_bindings | True | False | True |
| kb_directory_nodes | True | False | True |
| unified_task_events | True | False | True |
| unified_task_jobs | True | False | True |
| unified_tasks | True | False | True |
| paper_plag_hits | True | False | True |
| paper_plag_reports | True | False | True |
| paper_versions | True | False | True |
| egress_decision_audits | True | False | True |
| nas_import_tasks | True | False | True |
| backup_jobs | True | False | True |
| backup_locks | True | False | True |
| data_security_settings | True | False | True |
| org_directory_audit_logs | True | False | True |
| departments | True | False | True |
| companies | True | False | True |
| audit_events | True | False | True |
| deletion_logs | True | False | True |
| download_logs | True | False | True |
| search_configs | True | False | True |
| upload_settings | True | False | True |
| kb_documents | True | False | True |
| users | True | False | True |

