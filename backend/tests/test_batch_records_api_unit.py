from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
import unittest
from types import SimpleNamespace
from uuid import uuid4

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.batch_records.router import router as batch_records_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.batch_records import BatchRecordsService
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def __init__(self, users: dict[str, SimpleNamespace]):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)


class _Deps:
    def __init__(self, *, db_path: str, users: dict[str, SimpleNamespace]):
        self.user_store = _UserStore(users)
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)

        self.batch_records_service = BatchRecordsService(db_path=db_path)
        self.electronic_signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))

        self.audit_log_store = AuditLogStore(db_path=db_path)
        self.audit_log_manager = AuditLogManager(store=self.audit_log_store)


def _make_user(*, user_id: str, role: str) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        status="active",
        group_id=None,
        group_ids=[],
        tool_ids=[],
        company_id=1,
        department_id=1,
    )


def _issue_sign_token(*, db_path: str, user_id: str, ttl_ms: int = 60_000) -> str:
    now_ms = int(time.time() * 1000)
    token_id = str(uuid4())
    sign_token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(sign_token.encode("utf-8")).hexdigest()
    store = ElectronicSignatureStore(db_path=db_path)
    store.create_challenge(
        token_id=token_id,
        user_id=str(user_id),
        token_hash=token_hash,
        issued_at_ms=now_ms,
        expires_at_ms=now_ms + int(ttl_ms),
    )
    return sign_token


class TestBatchRecordsApiUnit(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(batch_records_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_happy_path_template_execution_sign_review_export_and_audit(self):
        td = make_temp_dir(prefix="ragflowauth_batch_records_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "viewer-1": _make_user(user_id="viewer-1", role="viewer"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_template = client.post(
                    "/api/quality-system/batch-records/templates",
                    json={
                        "template_code": "BR-TPL-001",
                        "template_name": "Production Batch Record",
                        "steps": [
                            {"key": "mix", "title": "Mixing"},
                            {"key": "pack", "title": "Packing"},
                        ],
                        "meta": {"product": "P1"},
                    },
                )
                self.assertEqual(create_template.status_code, 200, create_template.text)
                template = create_template.json()["template"]
                template_id = template["template_id"]

                publish_template = client.post(
                    f"/api/quality-system/batch-records/templates/{template_id}/publish",
                )
                self.assertEqual(publish_template.status_code, 200, publish_template.text)
                self.assertEqual(publish_template.json()["template"]["status"], "active")

                create_execution = client.post(
                    "/api/quality-system/batch-records/executions",
                    json={"template_id": template_id, "batch_no": "B-0001"},
                )
                self.assertEqual(create_execution.status_code, 200, create_execution.text)
                execution_id = create_execution.json()["bundle"]["execution"]["execution_id"]

                write_step = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/steps",
                    json={
                        "step_key": "mix",
                        "payload": {
                            "operator": "op1",
                            "result": "ok",
                            "photo_evidences": [
                                {
                                    "filename": "mix.jpg",
                                    "media_type": "image/jpeg",
                                    "data_url": "data:image/jpeg;base64,"
                                    + base64.b64encode(b"mix-photo").decode("ascii"),
                                    "captured_at_ms": 123,
                                }
                            ],
                        },
                    },
                )
                self.assertEqual(write_step.status_code, 200, write_step.text)
                bundle = write_step.json()["bundle"]
                self.assertIn("mix", bundle["latest_steps"])
                evidence = bundle["latest_steps"]["mix"]["payload"]["photo_evidences"][0]
                self.assertEqual(evidence["filename"], "mix.jpg")
                self.assertEqual(evidence["media_type"], "image/jpeg")
                self.assertEqual(evidence["captured_at_ms"], 123)
                self.assertEqual(evidence["size_bytes"], len(b"mix-photo"))
                self.assertEqual(evidence["sha256"], hashlib.sha256(b"mix-photo").hexdigest())

                export_early = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/export",
                )
                self.assertEqual(export_early.status_code, 409, export_early.text)
                self.assertEqual(export_early.json()["detail"], "batch_record_execution_not_ready_for_export")

                sign_token = _issue_sign_token(db_path=db_path, user_id="admin-1")
                sign_resp = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/sign",
                    json={
                        "sign_token": sign_token,
                        "meaning": "Operator sign-off",
                        "reason": "All steps completed",
                    },
                )
                self.assertEqual(sign_resp.status_code, 200, sign_resp.text)
                self.assertEqual(sign_resp.json()["bundle"]["execution"]["status"], "signed")
                signed_signature_id = sign_resp.json()["bundle"]["execution"]["signed_signature_id"]
                self.assertTrue(signed_signature_id)

                review_token = _issue_sign_token(db_path=db_path, user_id="admin-1")
                review_resp = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/review",
                    json={
                        "sign_token": review_token,
                        "meaning": "QA review",
                        "reason": "Record verified",
                    },
                )
                self.assertEqual(review_resp.status_code, 200, review_resp.text)
                self.assertEqual(review_resp.json()["bundle"]["execution"]["status"], "reviewed")
                reviewed_signature_id = review_resp.json()["bundle"]["execution"]["reviewed_signature_id"]
                self.assertTrue(reviewed_signature_id)

                export_resp = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/export",
                )
                self.assertEqual(export_resp.status_code, 200, export_resp.text)
                payload = export_resp.json()
                self.assertTrue(payload["filename"].startswith("batch-record-"))
                self.assertEqual(payload["export"]["execution"]["execution_id"], execution_id)
                self.assertIn("signed_signature", payload["export"])
                self.assertIn("reviewed_signature", payload["export"])

            total, rows = deps.audit_log_store.list_events(source="batch_records", limit=200)
            self.assertGreater(total, 0)
            actions = {r.action for r in rows}
            expected = {
                "batch_record_template_create",
                "batch_record_template_publish",
                "batch_record_execution_create",
                "batch_record_step_write",
                "batch_record_execution_sign",
                "batch_record_execution_review",
                "batch_record_execution_export",
            }
            self.assertTrue(expected.issubset(actions), f"missing_actions={expected - actions}")

        finally:
            cleanup_dir(td)

    def test_forbidden_user_cannot_manage_template_or_sign_or_review(self):
        td = make_temp_dir(prefix="ragflowauth_batch_records_forbidden")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "viewer-1": _make_user(user_id="viewer-1", role="viewer"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_template = client.post(
                    "/api/quality-system/batch-records/templates",
                    json={
                        "template_code": "BR-TPL-002",
                        "template_name": "Inspection Batch Record",
                        "steps": [{"key": "inspect", "title": "Inspection"}],
                        "meta": {},
                    },
                )
                template_id = create_template.json()["template"]["template_id"]
                client.post(f"/api/quality-system/batch-records/templates/{template_id}/publish")
                create_execution = client.post(
                    "/api/quality-system/batch-records/executions",
                    json={"template_id": template_id, "batch_no": "B-0002"},
                )
                execution_id = create_execution.json()["bundle"]["execution"]["execution_id"]

            viewer_app = self._build_app(current_user_id="viewer-1", deps=deps)
            with TestClient(viewer_app) as client:
                resp = client.post(
                    "/api/quality-system/batch-records/templates",
                    json={
                        "template_code": "BR-TPL-FORBIDDEN",
                        "template_name": "Forbidden",
                        "steps": [{"key": "s1", "title": "Step"}],
                        "meta": {},
                    },
                )
                self.assertEqual(resp.status_code, 403, resp.text)

                sign_token = _issue_sign_token(db_path=db_path, user_id="viewer-1")
                sign_resp = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/sign",
                    json={
                        "sign_token": sign_token,
                        "meaning": "Sign",
                        "reason": "Try",
                    },
                )
                self.assertEqual(sign_resp.status_code, 403, sign_resp.text)

                review_token = _issue_sign_token(db_path=db_path, user_id="viewer-1")
                review_resp = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/review",
                    json={
                        "sign_token": review_token,
                        "meaning": "Review",
                        "reason": "Try",
                    },
                )
                self.assertEqual(review_resp.status_code, 403, review_resp.text)
        finally:
            cleanup_dir(td)

    def test_invalid_photo_evidence_is_rejected(self):
        td = make_temp_dir(prefix="ragflowauth_batch_records_photo_invalid")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {"admin-1": _make_user(user_id="admin-1", role="admin")}
            deps = _Deps(db_path=db_path, users=users)

            app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(app) as client:
                create_template = client.post(
                    "/api/quality-system/batch-records/templates",
                    json={
                        "template_code": "BR-TPL-003",
                        "template_name": "Photo Validation",
                        "steps": [{"key": "mix", "title": "Mixing"}],
                        "meta": {},
                    },
                )
                template_id = create_template.json()["template"]["template_id"]
                client.post(f"/api/quality-system/batch-records/templates/{template_id}/publish")
                create_execution = client.post(
                    "/api/quality-system/batch-records/executions",
                    json={"template_id": template_id, "batch_no": "B-0003"},
                )
                execution_id = create_execution.json()["bundle"]["execution"]["execution_id"]

                response = client.post(
                    f"/api/quality-system/batch-records/executions/{execution_id}/steps",
                    json={
                        "step_key": "mix",
                        "payload": {
                            "photo_evidences": [
                                {
                                    "filename": "mix.txt",
                                    "media_type": "text/plain",
                                    "data_url": "data:text/plain;base64,"
                                    + base64.b64encode(b"not-an-image").decode("ascii"),
                                }
                            ]
                        },
                    },
                )

            self.assertEqual(response.status_code, 400, response.text)
            self.assertEqual(response.json()["detail"], "step_photo_media_type_invalid")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
