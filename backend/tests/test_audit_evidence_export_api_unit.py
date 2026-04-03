import hashlib
import io
import json
import os
import unittest
from types import SimpleNamespace
from zipfile import ZipFile

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.audit.router import router as audit_router
from backend.database.schema.ensure import ensure_schema
from backend.services.approval import ApprovalWorkflowStore
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.data_security import DataSecurityStore
from backend.services.electronic_signature import ElectronicSignatureStore
from backend.services.notification import NotificationStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self, *, role: str):
        self.user_id = "u-admin" if role == "admin" else "u-viewer"
        self.username = "admin1" if role == "admin" else "viewer1"
        self.email = f"{self.username}@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.company_id = 1
        self.department_id = 2


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _UserKbPermissionStore:
    def get_user_kbs(self, user_id: str):  # noqa: ARG002
        return []


class _UserChatPermissionStore:
    def get_user_chats(self, user_id: str):  # noqa: ARG002
        return []


class _Deps:
    def __init__(self, *, db_path: str, role: str):
        audit_store = AuditLogStore(db_path=db_path)
        self.user_store = _UserStore(_User(role=role))
        self.permission_group_store = _PermissionGroupStore()
        self.user_kb_permission_store = _UserKbPermissionStore()
        self.user_chat_permission_store = _UserChatPermissionStore()
        self.audit_log_store = audit_store
        self.audit_log_manager = AuditLogManager(store=audit_store)


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u-admin")


def _seed_evidence(db_path: str) -> None:
    audit_store = AuditLogStore(db_path=db_path)
    approval_store = ApprovalWorkflowStore(db_path=db_path)
    signature_store = ElectronicSignatureStore(db_path=db_path)
    notification_store = NotificationStore(db_path=db_path)
    data_security_store = DataSecurityStore(db_path=db_path)

    audit_store.log_event(
        action="document_preview",
        actor="u-admin",
        actor_username="admin1",
        company_id=1,
        company_name="Acme",
        department_id=2,
        department_name="QA",
        resource_type="knowledge_document",
        resource_id="doc-fda02",
        event_type="preview",
        source="knowledge",
        doc_id="doc-fda02",
        filename="evidence.txt",
        request_id="rid-fda02",
        meta={"inspection": True},
    )
    approval_store.upsert_workflow(
        workflow_id="wf-fda02",
        kb_ref="kb-a",
        name="FDA-02 Workflow",
        steps=[
            {"step_no": 1, "step_name": "Step 1", "approver_user_id": "u-admin"},
            {"step_no": 2, "step_name": "Step 2", "approver_user_id": "u-b"},
        ],
        is_active=True,
    )
    instance = approval_store.create_instance(doc_id="doc-fda02", workflow_id="wf-fda02")
    approval_store.record_action(
        instance_id=str(instance["instance_id"]),
        doc_id="doc-fda02",
        workflow_id="wf-fda02",
        step_no=1,
        action="approve",
        actor="u-admin",
        notes="approved for export test",
    )
    signature_store.create_signature(
        signature_id="sig-fda02",
        record_type="document_review",
        record_id="doc-fda02",
        action="approve",
        meaning="Approval",
        reason="Inspection export",
        signed_by="u-admin",
        signed_by_username="admin1",
        signed_at_ms=1710000000000,
        sign_token_id="token-fda02",
        record_hash="record-hash-fda02",
        signature_hash="signature-hash-fda02",
        status="signed",
        record_payload_json=json.dumps({"doc_id": "doc-fda02", "filename": "evidence.txt"}, ensure_ascii=False),
    )
    notification_store.upsert_channel(
        channel_id="email-main",
        channel_type="email",
        name="Main Email",
        enabled=True,
        config={"from_email": "qa@example.com"},
    )
    job = notification_store.create_job(
        channel_id="email-main",
        event_type="review_todo_approval",
        payload={
            "doc_id": "doc-fda02",
            "filename": "evidence.txt",
            "approval_target": {"doc_id": "doc-fda02", "route_path": "/documents?tab=approve&doc_id=doc-fda02"},
        },
        recipient_user_id="u-admin",
        recipient_username="admin1",
        recipient_address="admin1@example.com",
        dedupe_key="review_todo_approval:doc-fda02",
    )
    notification_store.add_delivery_log(
        job_id=int(job["job_id"]),
        channel_id="email-main",
        status="sent",
        error=None,
    )
    backup_job = data_security_store.create_job_v2(kind="full", status="completed", message="backup ok")
    data_security_store.update_job(
        backup_job.id,
        output_dir="D:/backup/fda02",
        package_hash="pkg-hash-fda02",
        verification_status="passed",
        verification_detail="restore verified",
        replication_status="completed",
        replica_path="D:/replica/fda02",
    )
    data_security_store.create_restore_drill(
        job_id=backup_job.id,
        backup_path="D:/backup/fda02/package.zip",
        backup_hash="pkg-hash-fda02",
        actual_backup_hash="pkg-hash-fda02",
        hash_match=True,
        restore_target="inspection-target",
        restored_auth_db_path="D:/restore/auth.db",
        restored_auth_db_hash="restore-hash-fda02",
        compare_match=True,
        package_validation_status="passed",
        acceptance_status="passed",
        executed_by="u-admin",
        result="success",
        verification_notes="verification ok",
        verification_report={"auth_db_hash_match": True},
    )


class TestAuditEvidenceExportApiUnit(unittest.TestCase):
    def test_admin_can_export_portable_evidence_package_with_manifest_hashes(self):
        td = make_temp_dir(prefix="ragflowauth_fda02_export")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            _seed_evidence(db_path)

            app = FastAPI()
            app.state.deps = _Deps(db_path=db_path, role="admin")
            app.include_router(audit_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/audit/evidence-export?doc_id=doc-fda02")

            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(resp.headers["content-type"], "application/zip")
            self.assertIn("inspection_evidence_doc-fda02_", resp.headers["content-disposition"])
            self.assertEqual(hashlib.sha256(resp.content).hexdigest(), resp.headers["x-evidence-package-sha256"])

            archive = ZipFile(io.BytesIO(resp.content))
            members = set(archive.namelist())
            self.assertIn("manifest.json", members)
            self.assertIn("checksums.json", members)
            self.assertIn("audit_events.csv", members)
            self.assertIn("electronic_signatures.json", members)
            self.assertIn("approval_actions.csv", members)
            self.assertIn("notification_jobs.json", members)
            self.assertIn("backup_jobs.csv", members)
            self.assertIn("restore_drills.json", members)

            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            checksums = json.loads(archive.read("checksums.json").decode("utf-8"))
            self.assertEqual(manifest["counts"]["audit_events"], 1)
            self.assertEqual(manifest["counts"]["electronic_signatures"], 1)
            self.assertEqual(manifest["counts"]["approval_actions"], 1)
            self.assertEqual(manifest["counts"]["notification_jobs"], 1)
            self.assertEqual(manifest["counts"]["backup_jobs"], 1)
            self.assertEqual(manifest["counts"]["restore_drills"], 1)
            self.assertEqual(manifest["metadata"]["filters"]["doc_id"], "doc-fda02")
            self.assertEqual(manifest["metadata"]["record_copy_definition"]["human_readable_copy"], "csv")
            self.assertEqual(manifest["metadata"]["record_copy_definition"]["portable_structured_copy"], "json")
            self.assertEqual(manifest["files"], checksums)

            audit_csv_bytes = archive.read("audit_events.csv")
            self.assertEqual(
                hashlib.sha256(audit_csv_bytes).hexdigest(),
                manifest["files"]["audit_events.csv"]["sha256"],
            )
            audit_events = json.loads(archive.read("audit_events.json").decode("utf-8"))
            self.assertEqual(audit_events[0]["doc_id"], "doc-fda02")
            notifications = json.loads(archive.read("notification_jobs.json").decode("utf-8"))
            self.assertEqual(notifications[0]["payload"]["approval_target"]["doc_id"], "doc-fda02")
            self.assertEqual(len(notifications[0]["delivery_logs"]), 1)
            restore_drills = json.loads(archive.read("restore_drills.json").decode("utf-8"))
            self.assertEqual(restore_drills[0]["acceptance_status"], "passed")

            exported_events = app.state.deps.audit_log_store.list_events(action="audit_evidence_export", limit=10)[1]
            self.assertEqual(len(exported_events), 1)
            self.assertEqual(exported_events[0].resource_type, "inspection_evidence_package")
        finally:
            cleanup_dir(td)

    def test_non_admin_cannot_export_evidence_package(self):
        td = make_temp_dir(prefix="ragflowauth_fda02_export_deny")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            _seed_evidence(db_path)

            app = FastAPI()
            app.state.deps = _Deps(db_path=db_path, role="viewer")
            app.include_router(audit_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/audit/evidence-export?doc_id=doc-fda02")

            self.assertEqual(resp.status_code, 403, resp.text)
            self.assertEqual(resp.json()["detail"], "admin_required")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
