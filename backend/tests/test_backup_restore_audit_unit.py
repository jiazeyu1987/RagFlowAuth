from __future__ import annotations

import os
import re
import shutil
import sqlite3
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
    def _write_restore_probe(self, db_path: Path, value: str) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS restore_probe (value TEXT NOT NULL)")
            conn.execute("DELETE FROM restore_probe")
            conn.execute("INSERT INTO restore_probe(value) VALUES (?)", (value,))
            conn.commit()
        finally:
            conn.close()

    def _read_restore_probe(self, db_path: Path) -> str | None:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute("SELECT value FROM restore_probe LIMIT 1").fetchone()
            return str(row[0]) if row else None
        finally:
            conn.close()

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
            replicate_mock = stack.enter_context(
                patch(
                    "backend.services.data_security.replica_service.BackupReplicaService.replicate_backup",
                    side_effect=AssertionError("formal_backup_should_not_use_windows_replica"),
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
            "replicate_mock": replicate_mock,
        }

    def test_backup_service_completes_when_local_backup_succeeds(self):
        result = self._run_backup_job()
        try:
            after = result["job"]
            self.assertEqual(after.status, "completed")
            self.assertEqual(after.message, "backup_completed_local")
            self.assertTrue(after.output_dir)
            self.assertIsNone(after.replication_status)
            self.assertIsNone(after.replication_error)
            self.assertFalse(after.replica_path)
            self.assertIsNotNone(after.package_hash)
            self.assertRegex(str(after.package_hash), r"^[0-9a-f]{64}$")
            self.assertEqual(after.package_hash, _compute_backup_package_hash(result["package_dir"]))
            result["replicate_mock"].assert_not_called()
        finally:
            cleanup_dir(result["td"])

    def test_backup_service_fails_when_local_backup_fails(self):
        def _local_fail(*, pack_dir: Path, local_root: Path):
            raise RuntimeError("local_move_failed")

        result = self._run_backup_job(
            finalize_side_effect=_local_fail,
        )
        try:
            after = result["job"]
            self.assertEqual(after.status, "failed")
            self.assertEqual(after.message, "backup_failed_local")
            self.assertFalse(after.output_dir)
            self.assertIsNone(after.replication_status)
            self.assertIn("local_backup_failed:local_move_failed", str(after.detail))
            result["replicate_mock"].assert_not_called()
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

    def test_real_restore_router_overwrites_live_auth_db(self):
        td = make_temp_dir(prefix="ragflowauth_real_restore")
        try:
            db_path = Path(td) / "auth.db"
            ensure_schema(str(db_path))
            store = DataSecurityStore(db_path=str(db_path))
            store.update_settings({"auth_db_path": str(db_path)})
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            self._write_restore_probe(db_path, "live-before")

            pack_dir = Path(td) / "migration_pack_real"
            pack_dir.mkdir(parents=True, exist_ok=True)
            backup_auth_db = pack_dir / "auth.db"
            shutil.copy2(db_path, backup_auth_db)
            self._write_restore_probe(backup_auth_db, "from-backup")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            pack_hash = _compute_backup_package_hash(pack_dir)
            store.update_job(base_job.id, output_dir=str(pack_dir), package_hash=pack_hash)
            qualify_user_for_action(str(db_path), user_id="u1", action_code="restore_drill_execute")

            audit_mgr = _AuditLogManagerStub()
            deps = _Deps(store=store, audit_mgr=audit_mgr, db_path=str(db_path))

            app = FastAPI()
            app.state.deps = deps
            app.include_router(data_security_router.router, prefix="/api")
            app.dependency_overrides[authz_module.admin_only] = _override_admin_only

            with TestClient(app) as client:
                resp = client.post(
                    "/api/admin/data-security/restore/run",
                    json={
                        "job_id": base_job.id,
                        "backup_path": str(pack_dir),
                        "backup_hash": pack_hash,
                        "change_reason": "recover deleted user",
                        "confirmation_text": "RESTORE",
                    },
                )
                self.assertEqual(resp.status_code, 200, resp.text)
                payload = resp.json()
                self.assertEqual(payload["result"], "success")
                self.assertTrue(payload["hash_match"])
                self.assertTrue(payload["compare_match"])
                self.assertEqual(payload["live_auth_db_path"], str(db_path))
                self.assertEqual(payload["source_auth_db_path"], str(backup_auth_db))

            self.assertEqual(self._read_restore_probe(db_path), "from-backup")
            self.assertEqual(self._read_restore_probe(backup_auth_db), "from-backup")

            actions = [str(item.get("action") or "") for item in audit_mgr.events]
            self.assertIn("backup_restore_execute", actions)
            restore_events = [item for item in audit_mgr.events if item.get("action") == "backup_restore_execute"]
            self.assertEqual(len(restore_events), 1)
            self.assertEqual(restore_events[0]["meta"]["job_id"], base_job.id)
            self.assertTrue(restore_events[0]["meta"]["compare_match"])
        finally:
            cleanup_dir(td)

    def test_real_restore_rejects_invalid_confirmation(self):
        td = make_temp_dir(prefix="ragflowauth_real_restore_confirm")
        try:
            db_path = Path(td) / "auth.db"
            ensure_schema(str(db_path))
            store = DataSecurityStore(db_path=str(db_path))
            store.update_settings({"auth_db_path": str(db_path)})
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_invalid_confirmation"
            pack_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, pack_dir / "auth.db")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            pack_hash = _compute_backup_package_hash(pack_dir)
            store.update_job(base_job.id, output_dir=str(pack_dir), package_hash=pack_hash)
            qualify_user_for_action(str(db_path), user_id="u1", action_code="restore_drill_execute")

            audit_mgr = _AuditLogManagerStub()
            deps = _Deps(store=store, audit_mgr=audit_mgr, db_path=str(db_path))

            app = FastAPI()
            app.state.deps = deps
            app.include_router(data_security_router.router, prefix="/api")
            app.dependency_overrides[authz_module.admin_only] = _override_admin_only

            with TestClient(app) as client:
                resp = client.post(
                    "/api/admin/data-security/restore/run",
                    json={
                        "job_id": base_job.id,
                        "backup_path": str(pack_dir),
                        "backup_hash": pack_hash,
                        "change_reason": "recover deleted user",
                        "confirmation_text": "WRONG",
                    },
                )
                self.assertEqual(resp.status_code, 400, resp.text)
                self.assertEqual(resp.json().get("detail"), "restore_confirmation_text_invalid")
        finally:
            cleanup_dir(td)

    def test_real_restore_rejects_missing_change_reason(self):
        td = make_temp_dir(prefix="ragflowauth_real_restore_reason")
        try:
            db_path = Path(td) / "auth.db"
            ensure_schema(str(db_path))
            store = DataSecurityStore(db_path=str(db_path))
            store.update_settings({"auth_db_path": str(db_path)})
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_missing_reason"
            pack_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, pack_dir / "auth.db")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            pack_hash = _compute_backup_package_hash(pack_dir)
            store.update_job(base_job.id, output_dir=str(pack_dir), package_hash=pack_hash)
            qualify_user_for_action(str(db_path), user_id="u1", action_code="restore_drill_execute")

            audit_mgr = _AuditLogManagerStub()
            deps = _Deps(store=store, audit_mgr=audit_mgr, db_path=str(db_path))

            app = FastAPI()
            app.state.deps = deps
            app.include_router(data_security_router.router, prefix="/api")
            app.dependency_overrides[authz_module.admin_only] = _override_admin_only

            with TestClient(app) as client:
                resp = client.post(
                    "/api/admin/data-security/restore/run",
                    json={
                        "job_id": base_job.id,
                        "backup_path": str(pack_dir),
                        "backup_hash": pack_hash,
                        "change_reason": "   ",
                        "confirmation_text": "RESTORE",
                    },
                )
                self.assertEqual(resp.status_code, 400, resp.text)
                self.assertEqual(resp.json().get("detail"), "change_reason_required")
        finally:
            cleanup_dir(td)

    def test_real_restore_rejects_when_backup_job_is_running(self):
        td = make_temp_dir(prefix="ragflowauth_real_restore_running_job")
        try:
            db_path = Path(td) / "auth.db"
            ensure_schema(str(db_path))
            store = DataSecurityStore(db_path=str(db_path))
            store.update_settings({"auth_db_path": str(db_path)})
            running_job = store.create_job_v2(kind="incremental", status="running", message="busy")
            base_job = store.create_job_v2(kind="full", status="completed", message="done")
            pack_dir = Path(td) / "migration_pack_running_conflict"
            pack_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, pack_dir / "auth.db")
            (pack_dir / "backup_settings.json").write_text('{"enabled": true}', encoding="utf-8")
            pack_hash = _compute_backup_package_hash(pack_dir)
            store.update_job(base_job.id, output_dir=str(pack_dir), package_hash=pack_hash)
            qualify_user_for_action(str(db_path), user_id="u1", action_code="restore_drill_execute")

            audit_mgr = _AuditLogManagerStub()
            deps = _Deps(store=store, audit_mgr=audit_mgr, db_path=str(db_path))

            app = FastAPI()
            app.state.deps = deps
            app.include_router(data_security_router.router, prefix="/api")
            app.dependency_overrides[authz_module.admin_only] = _override_admin_only

            with TestClient(app) as client:
                resp = client.post(
                    "/api/admin/data-security/restore/run",
                    json={
                        "job_id": base_job.id,
                        "backup_path": str(pack_dir),
                        "backup_hash": pack_hash,
                        "change_reason": "recover deleted user",
                        "confirmation_text": "RESTORE",
                    },
                )
                self.assertEqual(resp.status_code, 409, resp.text)
                self.assertEqual(
                    resp.json().get("detail"),
                    f"restore_requires_no_active_backup_job:{running_job.id}",
                )
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
