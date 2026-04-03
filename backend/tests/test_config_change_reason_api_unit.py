import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from backend.app.modules.data_security.router import update_settings as update_data_security_settings
from backend.app.modules.knowledge.routes.upload import update_allowed_extensions


class _Request:
    def __init__(self):
        self.state = SimpleNamespace(request_id="rid-1")
        self.client = SimpleNamespace(host="127.0.0.1")


class _UploadSettingsStore:
    def get(self):
        return SimpleNamespace(allowed_extensions=[".pdf"], updated_at_ms=1)

    def update_allowed_extensions(self, extensions, *, changed_by=None, change_reason=None):  # noqa: ARG002
        return SimpleNamespace(allowed_extensions=list(extensions or []), updated_at_ms=2)


class _DataSecurityStore:
    def __init__(self):
        self.settings = SimpleNamespace(
            enabled=False,
            interval_minutes=1440,
            target_mode="local",
            target_ip="",
            target_share_name="",
            target_subdir="",
            target_local_dir="/backup",
            ragflow_compose_path="docker-compose.yml",
            ragflow_project_name="ragflow",
            ragflow_stop_services=False,
            auth_db_path="data/auth.db",
            updated_at_ms=1,
            last_run_at_ms=None,
            upload_after_backup=False,
            upload_host=None,
            upload_username=None,
            upload_target_path=None,
            full_backup_enabled=False,
            full_backup_include_images=True,
            backup_retention_max=30,
            incremental_schedule=None,
            full_backup_schedule=None,
            last_incremental_backup_time_ms=None,
            last_full_backup_time_ms=None,
            replica_enabled=False,
            replica_target_path=None,
            replica_subdir_format="flat",
        )

    def get_settings(self):
        return self.settings

    def update_settings(self, updates, *, changed_by=None, change_reason=None):  # noqa: ARG002
        return self.settings


class _AuditLogManager:
    def log_event(self, **kwargs):  # noqa: ARG002
        return None


class _UserStore:
    def get_by_user_id(self, user_id):  # noqa: ARG002
        return SimpleNamespace(user_id="admin-1", username="admin", company_id=None, department_id=None)


class TestConfigChangeReasonApiUnit(unittest.TestCase):
    def test_upload_settings_route_requires_change_reason(self):
        ctx = SimpleNamespace(
            snapshot=SimpleNamespace(is_admin=True),
            payload=SimpleNamespace(sub="admin-1"),
            user=SimpleNamespace(username="admin", company_id=None, department_id=None),
            deps=SimpleNamespace(
                upload_settings_store=_UploadSettingsStore(),
                audit_log_manager=_AuditLogManager(),
                org_directory_store=SimpleNamespace(),
            ),
        )

        with self.assertRaises(HTTPException) as cm:
            update_allowed_extensions(_Request(), ctx, {"allowed_extensions": [".pdf", ".dwg"]})

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(cm.exception.detail, "change_reason_required")

    def test_data_security_route_requires_change_reason(self):
        deps = SimpleNamespace(
            data_security_store=_DataSecurityStore(),
            audit_log_manager=_AuditLogManager(),
            user_store=_UserStore(),
            org_directory_store=SimpleNamespace(),
        )

        with self.assertRaises(HTTPException) as cm:
            update_data_security_settings(
                payload=SimpleNamespace(sub="admin-1"),
                request=_Request(),
                body={"backup_retention_max": 45},
                deps=deps,
            )

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(cm.exception.detail, "change_reason_required")


if __name__ == "__main__":
    unittest.main()
