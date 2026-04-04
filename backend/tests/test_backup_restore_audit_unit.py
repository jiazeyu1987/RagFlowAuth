from __future__ import annotations

import os
import re
import shutil
import unittest
from contextlib import ExitStack
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
        self.org_structure_manager = self.org_directory_store


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

    def _run_backup_job(
        self,
        *,
        replica_enabled: bool,
        replica_side_effect,
        finalize_side_effect=None,
    ):
        td = make_temp_dir(prefix="ragflowauth_backup_hash")
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
        if not replica_enabled:
            store.update_settings({"replica_enabled": False})
        job = store.create_job_v2(kind="incremental", status="queued", message="queued")

        local_root = Path(td) / "local_backups"
        staging_root = local_root / "_staging" / f"job_{job.id}"
        staged_pack_dir = staging_root / "migration_pack_test"
        replica_dir = Path(td) / "windows_backups" / "migration_pack_test"

        def _fake_precheck(ctx):
            staged_pack_dir.mkdir(parents=True, exist_ok=True)
            ctx.target = str(local_root)
            ctx.local_backup_root = local_root
            ctx.staging_root = staging_root
            ctx.pack_dir = staged_pack_dir
            ctx.windows_target = "/mnt/replica/RagflowAuth"
            ctx.update(message="prepared", progress=3)

        def _fake_sqlite(_ctx):
            (staged_pack_dir / "auth.db").write_text("sqlite-bytes", encoding="utf-8")

        def _fake_volumes(_ctx):
            (staged_pack_dir / "volumes").mkdir(parents=True, exist_ok=True)
            (staged_pack_dir / "volumes" / "ragflow.tar.gz").write_text("vol", encoding="utf-8")

        def _fake_images(_ctx):
            return None

        def _fake_snapshot(_ctx):
            (staged_pack_dir / "backup_settings.json").write_text('{"ok": true}', encoding="utf-8")

        def _replica_wrapper(pack_dir: Path, job_id: int):
            return replica_side_effect(
                pack_dir=pack_dir,
                job_id=job_id,
                store=store,
                replica_dir=replica_dir,
            )

        svc = DataSecurityBackupService(store)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "backend.services.data_security.backup_service.backup_precheck_and_prepare",
                    side_effect=_fake_precheck,
                )
            )
            stack.enter_context(
                patch(
                    "backend.services.data_security.backup_service.backup_sqlite_db",
                    side_effect=_fake_sqlite,
                )
            )
            stack.enter_context(
                patch(
                    "backend.services.data_security.backup_service.backup_ragflow_volumes",
                    side_effect=_fake_volumes,
                )
            )
            stack.enter_context(
                patch(
                    "backend.services.data_security.backup_service.backup_docker_images",
                    side_effect=_fake_images,
                )
            )
            stack.enter_context(
                patch(
                    "backend.services.data_security.backup_service.write_backup_settings_snapshot",
                    side_effect=_fake_snapshot,
                )
            )
            stack.enter_context(
                patch(
                    "backend.services.data_security.backup_service.docker_ok",
                    return_value=(True, ""),
                )
            )
            stack.enter_context(
                patch(
                    "backend.services.data_security.models.LOCAL_BACKUP_TARGET_PATH",
                    str(local_root),
                )
            )
            if finalize_side_effect is not None:
                stack.enter_context(
                    patch(
                        "backend.services.data_security.backup_service._finalize_local_backup",
                        side_effect=finalize_side_effect,
                    )
                )
            stack.enter_context(
                patch(
                    "backend.services.data_security.replica_service.BackupReplicaService.replicate_backup",
                    side_effect=_replica_wrapper,
                )
            )
            svc.run_incremental_backup_job(job.id)

        after = store.get_job(job.id)
        package_dir = Path(after.output_dir) if after.output_dir else staged_pack_dir
        return {
            "td": td,
            "store": store,
            "job": after,
            "package_dir": package_dir,
            "local_root": local_root,
            "staged_pack_dir": staged_pack_dir,
            "replica_dir": replica_dir,
        }

    def test_backup_service_completes_when_local_succeeds_and_windows_fails(self):
        def _replica_fail(*, pack_dir: Path, job_id: int, store: DataSecurityStore, replica_dir: Path):
            self.assertTrue(pack_dir.exists())
            raise RuntimeError("windows_disk_full")

        result = self._run_backup_job(replica_enabled=True, replica_side_effect=_replica_fail)
        try:
            after = result["job"]
            self.assertEqual(after.status, "completed")
            self.assertEqual(after.message, "backup_completed_local_only")
            self.assertTrue(after.output_dir)
            self.assertEqual(after.replication_status, "failed")
            self.assertEqual(after.replication_error, "windows_disk_full")
            self.assertIsNotNone(after.package_hash)
            self.assertRegex(str(after.package_hash), r"^[0-9a-f]{64}$")
            self.assertEqual(after.package_hash, _compute_backup_package_hash(result["package_dir"]))
        finally:
            cleanup_dir(result["td"])

    def test_backup_service_completes_when_local_and_windows_succeed(self):
        def _replica_success(*, pack_dir: Path, job_id: int, store: DataSecurityStore, replica_dir: Path):
            replica_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(pack_dir, replica_dir, dirs_exist_ok=True)
            store.update_job(job_id, replication_status="succeeded", replica_path=str(replica_dir), replication_error="")
            return True

        result = self._run_backup_job(replica_enabled=True, replica_side_effect=_replica_success)
        try:
            after = result["job"]
            self.assertEqual(after.status, "completed")
            self.assertEqual(after.message, "backup_completed_local_and_windows")
            self.assertTrue(after.output_dir)
            self.assertEqual(after.replication_status, "succeeded")
            self.assertEqual(after.replica_path, str(result["replica_dir"]))
        finally:
            cleanup_dir(result["td"])

    def test_backup_service_completes_when_local_fails_and_windows_succeeds(self):
        def _replica_success(*, pack_dir: Path, job_id: int, store: DataSecurityStore, replica_dir: Path):
            replica_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(pack_dir, replica_dir, dirs_exist_ok=True)
            store.update_job(job_id, replication_status="succeeded", replica_path=str(replica_dir), replication_error="")
            return True

        def _local_fail(*, pack_dir: Path, local_root: Path):
            raise RuntimeError("local_move_failed")

        result = self._run_backup_job(
            replica_enabled=True,
            replica_side_effect=_replica_success,
            finalize_side_effect=_local_fail,
        )
        try:
            after = result["job"]
            self.assertEqual(after.status, "completed")
            self.assertEqual(after.message, "backup_completed_windows_only")
            self.assertFalse(after.output_dir)
            self.assertEqual(after.replication_status, "succeeded")
            self.assertEqual(after.replica_path, str(result["replica_dir"]))
            self.assertIn("local_backup_failed:local_move_failed", str(after.detail))
        finally:
            cleanup_dir(result["td"])

    def test_backup_service_fails_only_when_local_and_windows_both_fail(self):
        def _replica_fail(*, pack_dir: Path, job_id: int, store: DataSecurityStore, replica_dir: Path):
            raise RuntimeError("windows_copy_failed")

        def _local_fail(*, pack_dir: Path, local_root: Path):
            raise RuntimeError("local_move_failed")

        result = self._run_backup_job(
            replica_enabled=True,
            replica_side_effect=_replica_fail,
            finalize_side_effect=_local_fail,
        )
        try:
            after = result["job"]
            self.assertEqual(after.status, "failed")
            self.assertEqual(after.message, "backup_failed_local_and_windows")
            self.assertFalse(after.output_dir)
            self.assertEqual(after.replication_status, "failed")
            self.assertIn("local_backup_failed:local_move_failed", str(after.detail))
            self.assertIn("windows_backup_failed:windows_copy_failed", str(after.detail))
        finally:
            cleanup_dir(result["td"])

    def test_backup_service_marks_windows_skipped_when_replica_not_enabled(self):
        def _replica_skip(*, pack_dir: Path, job_id: int, store: DataSecurityStore, replica_dir: Path):
            store.update_job(job_id, replication_status="skipped", replication_error="replica_disabled")
            return False

        result = self._run_backup_job(replica_enabled=False, replica_side_effect=_replica_skip)
        try:
            after = result["job"]
            self.assertEqual(after.status, "completed")
            self.assertEqual(after.message, "backup_completed_local_only")
            self.assertTrue(after.output_dir)
            self.assertEqual(after.replication_status, "skipped")
        finally:
            cleanup_dir(result["td"])

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

    def test_restore_drill_rejects_non_local_backup_path(self):
        td = make_temp_dir(prefix="ragflowauth_restore_local_only")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = DataSecurityStore(db_path=db_path)
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_local"
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
                        "backup_path": str(Path(td) / "windows_copy"),
                        "backup_hash": pack_hash,
                        "restore_target": "qa-staging",
                    },
                )
                self.assertEqual(create_resp.status_code, 400, create_resp.text)
                self.assertEqual(create_resp.json().get("detail"), "restore_drill_backup_path_must_match_local_backup")
        finally:
            cleanup_dir(td)

    def test_restore_drill_rejects_jobs_without_local_backup(self):
        td = make_temp_dir(prefix="ragflowauth_restore_missing_local")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = DataSecurityStore(db_path=db_path)
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_windows_only"
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "auth.db").write_text("sqlite-data", encoding="utf-8")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            pack_hash = _compute_backup_package_hash(pack_dir)
            store.update_job(base_job.id, replica_path=str(pack_dir), package_hash=pack_hash, replication_status="succeeded")
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
                    },
                )
                self.assertEqual(create_resp.status_code, 400, create_resp.text)
                self.assertEqual(create_resp.json().get("detail"), "restore_drill_requires_local_backup")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
