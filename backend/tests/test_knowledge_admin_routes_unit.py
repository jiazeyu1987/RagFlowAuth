import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.knowledge.routes.admin import router as admin_router


class _User:
    def __init__(self, *, role: str = "admin"):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _DeletionLog:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _DeletionLogStore:
    def __init__(self, logs):
        self._logs = logs

    def list_deletions(self, **kwargs):  # noqa: ARG002
        return self._logs


class _OperationApprovalService:
    async def create_request(self, *, operation_type, ctx, **kwargs):
        return {
            "request_id": "req-1",
            "operation_type": operation_type,
            "operation_label": operation_type,
            "status": "in_approval",
            "current_step_no": 1,
            "current_step_name": "review",
            "submitted_at_ms": 1,
            "target_ref": str(kwargs.get("doc_id") or ""),
            "target_label": "",
            "applicant_user_id": ctx.payload.sub,
            "applicant_username": "u1",
            "summary": {},
            "last_error": None,
        }


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestKnowledgeAdminRoutesUnit(unittest.TestCase):
    def _make_client(self, *, role: str = "admin", logs=None):
        app = FastAPI()
        app.state.deps = SimpleNamespace(
            user_store=_UserStore(_User(role=role)),
            deletion_log_store=_DeletionLogStore(logs or []),
            operation_approval_service=_OperationApprovalService(),
        )
        app.include_router(admin_router, prefix="/api/knowledge")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_delete_document_returns_request_envelope(self):
        with self._make_client() as client:
            resp = client.delete("/api/knowledge/documents/doc-1")
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json()["request"]["request_id"], "req-1")
        self.assertEqual(resp.json()["request"]["operation_type"], "knowledge_file_delete")

    def test_list_deletions_returns_contract(self):
        logs = [
            _DeletionLog(
                id=1,
                doc_id="doc-1",
                filename="demo.txt",
                kb_id="kb-1",
                deleted_by="u1",
                deleted_at_ms=123,
                original_uploader="u2",
                original_reviewer="u3",
                ragflow_doc_id="rag-1",
                kb_name="KB-1",
            )
        ]
        with patch(
            "backend.app.modules.knowledge.routes.admin.resolve_user_display_names",
            return_value={"u1": "Admin", "u2": "Uploader", "u3": "Reviewer"},
        ):
            with self._make_client(logs=logs) as client:
                resp = client.get("/api/knowledge/deletions")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(
            resp.json(),
            {
                "deletions": [
                    {
                        "id": 1,
                        "doc_id": "doc-1",
                        "filename": "demo.txt",
                        "kb_id": "KB-1",
                        "deleted_by": "u1",
                        "deleted_by_name": "Admin",
                        "deleted_at_ms": 123,
                        "original_uploader": "u2",
                        "original_uploader_name": "Uploader",
                        "original_reviewer": "u3",
                        "original_reviewer_name": "Reviewer",
                        "ragflow_doc_id": "rag-1",
                    }
                ],
                "count": 1,
            },
        )

    def test_list_deletions_fails_fast_when_user_lookup_fails(self):
        logs = [
            _DeletionLog(
                id=1,
                doc_id="doc-1",
                filename="demo.txt",
                kb_id="kb-1",
                deleted_by="u1",
                deleted_at_ms=123,
                original_uploader=None,
                original_reviewer=None,
                ragflow_doc_id=None,
                kb_name="KB-1",
            )
        ]
        with patch(
            "backend.app.modules.knowledge.routes.admin.resolve_user_display_names",
            side_effect=RuntimeError("user_display_lookup_failed"),
        ):
            with self._make_client(logs=logs) as client:
                resp = client.get("/api/knowledge/deletions")
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "user_display_lookup_failed")
