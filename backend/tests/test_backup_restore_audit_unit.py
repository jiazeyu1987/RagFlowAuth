from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core import authz as authz_module
from backend.app.modules.data_security import router as data_security_router
from backend.database.schema.ensure import ensure_schema
from backend.services.data_security.backup_service import (
    DataSecurityBackupService,
    _compute_backup_package_hash,
)
from backend.services.data_security.store import DataSecurityStore
from backend.services.training_compliance import TrainingComplianceService
from backend.tests._training_test_utils import qualify_user_for_action
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self):
        self.user_id = "u1"
        self.username = "admin"
        self.role = "admin"
        self.company_id = 1
        self.department_id = 1


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _AuditLogManagerStub:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def log_event(self, **kwargs):
        self.events.append(dict(kwargs))
        return None


class _Deps:
    def __init__(self, store: DataSecurityStore, audit_mgr: _AuditLogManagerStub, db_path: str):
        self.data_security_store = store
        self.audit_log_manager = audit_mgr
        self.user_store = _UserStore(_User())
        self.training_compliance_service = TrainingComplianceService(db_path=db_path)
        self.org_directory_store = SimpleNamespace(
            get_company=lambda *_args, **_kwargs: SimpleNamespace(name="Acme"),
            get_department=lambda *_args, **_kwargs: SimpleNamespace(name="QA"),
        )


def _override_admin_only() -> TokenPayload:
    return TokenPayload(sub="u1")


class TestBackupRestoreAuditUnit(unittest.TestCase):
    def test_backup_job_verification_fields_persist(self):
        td = make_temp_dir(prefix="ragflowauth_backup_audit")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = DataSecurityStore(db_path=db_path)

            job = store.create_job_v2(kind="incremental", status="completed", message="done")
            now_ms = 1_800_000_000_000
            updated = store.update_job(
                job.id,
                package_hash="abc123",
                verified_by="qa_user",
                verified_at_ms=now_ms,
            )

            self.assertEqual(updated.package_hash, "abc123")
            self.assertEqual(updated.verified_by, "qa_user")
            self.assertEqual(updated.verified_at_ms, now_ms)

            listed = store.list_jobs(limit=10)
            self.assertGreaterEqual(len(listed), 1)
            self.assertEqual(listed[0].package_hash, "abc123")
            self.assertEqual(listed[0].verified_by, "qa_user")
            self.assertEqual(listed[0].verified_at_ms, now_ms)
        finally:
            cleanup_dir(td)

    def test_backup_service_marks_job_failed_when_replication_required_and_copy_fails(self):
        td = make_temp_dir(prefix="ragflowauth_backup_hash")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = DataSecurityStore(db_path=db_path)
            store.update_settings(
                {
                    "replica_enabled": True,
                    "replica_target_path": "/mnt/replica/RagflowAuth",
                    "replica_subdir_format": "flat",
                }
            )
            job = store.create_job_v2(kind="incremental", status="queued", message="queued")

            pack_dir = Path(td) / "migration_pack_test"
            pack_dir.mkdir(parents=True, exist_ok=True)

            def _fake_precheck(ctx):
                ctx.pack_dir = pack_dir
                ctx.update(message="prepared", progress=3, output_dir=str(pack_dir))

            def _fake_sqlite(_ctx):
                (pack_dir / "auth.db").write_text("sqlite-bytes", encoding="utf-8")

            def _fake_volumes(_ctx):
                (pack_dir / "volumes").mkdir(parents=True, exist_ok=True)
                (pack_dir / "volumes" / "ragflow.tar.gz").write_text("vol", encoding="utf-8")

            def _fake_images(_ctx):
                return None

            def _fake_snapshot(_ctx):
                (pack_dir / "backup_settings.json").write_text('{"ok": true}', encoding="utf-8")

            svc = DataSecurityBackupService(store)
            with patch(
                "backend.services.data_security.backup_service.backup_precheck_and_prepare",
                side_effect=_fake_precheck,
            ), patch(
                "backend.services.data_security.backup_service.backup_sqlite_db",
                side_effect=_fake_sqlite,
            ), patch(
                "backend.services.data_security.backup_service.backup_ragflow_volumes",
                side_effect=_fake_volumes,
            ), patch(
                "backend.services.data_security.backup_service.backup_docker_images",
                side_effect=_fake_images,
            ), patch(
                "backend.services.data_security.backup_service.write_backup_settings_snapshot",
                side_effect=_fake_snapshot,
            ), patch(
                "backend.services.data_security.backup_service.docker_ok",
                return_value=(True, ""),
            ), patch(
                "backend.services.data_security.replica_service.BackupReplicaService.replicate_backup",
                return_value=False,
            ):
                svc.run_incremental_backup_job(job.id)

            after = store.get_job(job.id)
            self.assertEqual(after.status, "failed")
            self.assertIsNotNone(after.package_hash)
            self.assertRegex(str(after.package_hash), r"^[0-9a-f]{64}$")
            self.assertEqual(after.package_hash, _compute_backup_package_hash(pack_dir))
            self.assertEqual(after.replication_status, "failed")
            self.assertEqual(after.message, "backup_failed_replication_required")
        finally:
            cleanup_dir(td)

    def test_restore_drill_router_executes_real_verification_path(self):
        td = make_temp_dir(prefix="ragflowauth_restore_drill")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = DataSecurityStore(db_path=db_path)
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_1"
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "auth.db").write_text("sqlite-data", encoding="utf-8")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            pack_hash = _compute_backup_package_hash(pack_dir)
            store.update_job(base_job.id, output_dir=str(pack_dir), package_hash=pack_hash)
            qualify_user_for_action(db_path, user_id="u1", action_code="restore_drill_execute")

            audit_mgr = _AuditLogManagerStub()
            deps = _Deps(store=store, audit_mgr=audit_mgr, db_path=db_path)

            app = FastAPI()
            app.state.deps = deps
            app.include_router(data_security_router.router, prefix="/api")
            app.dependency_overrides[authz_module.admin_only] = _override_admin_only

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/admin/data-security/restore-drills",
                    json={
                        "job_id": base_job.id,
                        "backup_path": str(pack_dir),
                        "backup_hash": pack_hash,
                        "restore_target": "qa-staging",
                        "verification_notes": "restore ok",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                created = create_resp.json()
                self.assertTrue(str(created.get("drill_id", "")).startswith("restore_drill_"))
                self.assertEqual(created.get("job_id"), base_job.id)
                self.assertEqual(created.get("result"), "success")
                self.assertEqual(created.get("acceptance_status"), "passed")
                self.assertTrue(created.get("hash_match"))
                self.assertTrue(created.get("compare_match"))
                restored_auth_db_path = Path(created["restored_auth_db_path"])
                self.assertTrue(restored_auth_db_path.exists())

                list_resp = client.get("/api/admin/data-security/restore-drills?limit=10")
                self.assertEqual(list_resp.status_code, 200, list_resp.text)
                listed = list_resp.json()
                self.assertEqual(listed.get("count"), 1)
                self.assertEqual(listed["items"][0]["drill_id"], created["drill_id"])

            verified_job = store.get_job(base_job.id)
            self.assertEqual(verified_job.verified_by, "u1")
            self.assertIsNotNone(verified_job.verified_at_ms)
            self.assertEqual(verified_job.verification_status, "passed")

            actions = [str(item.get("action") or "") for item in audit_mgr.events]
            self.assertIn("backup_restore_drill_create", actions)
            self.assertIn("backup_restore_drill_list", actions)

            create_events = [item for item in audit_mgr.events if item.get("action") == "backup_restore_drill_create"]
            self.assertEqual(len(create_events), 1)
            self.assertEqual(create_events[0].get("resource_type"), "restore_drill")
            self.assertEqual(create_events[0].get("event_type"), "create")
            self.assertEqual(create_events[0]["meta"]["acceptance_status"], "passed")
        finally:
            cleanup_dir(td)

    def test_restore_drill_blocks_tampered_backup_package(self):
        td = make_temp_dir(prefix="ragflowauth_restore_tampered")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = DataSecurityStore(db_path=db_path)
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_2"
            pack_dir.mkdir(parents=True, exist_ok=True)
            auth_db = pack_dir / "auth.db"
            auth_db.write_text("sqlite-data", encoding="utf-8")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            original_hash = _compute_backup_package_hash(pack_dir)
            auth_db.write_text("tampered-data", encoding="utf-8")
            store.update_job(base_job.id, output_dir=str(pack_dir), package_hash=original_hash)
            qualify_user_for_action(db_path, user_id="u1", action_code="restore_drill_execute")

            audit_mgr = _AuditLogManagerStub()
            deps = _Deps(store=store, audit_mgr=audit_mgr, db_path=db_path)

            app = FastAPI()
            app.state.deps = deps
            app.include_router(data_security_router.router, prefix="/api")
            app.dependency_overrides[authz_module.admin_only] = _override_admin_only

            with TestClient(app) as client:
                create_resp = client.post(
                    "/api/admin/data-security/restore-drills",
                    json={
                        "job_id": base_job.id,
                        "backup_path": str(pack_dir),
                        "backup_hash": original_hash,
                        "restore_target": "qa-staging",
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                created = create_resp.json()
                self.assertEqual(created.get("result"), "failed")
                self.assertEqual(created.get("acceptance_status"), "blocked")
                self.assertFalse(created.get("hash_match"))
                self.assertFalse(created.get("compare_match"))
                self.assertEqual(created.get("package_validation_status"), "blocked")
                self.assertEqual(created.get("restored_auth_db_path"), None)

            verified_job = store.get_job(base_job.id)
            self.assertIsNone(verified_job.verified_by)
            self.assertIsNone(verified_job.verified_at_ms)
            self.assertEqual(verified_job.verification_status, "blocked")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
