import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.knowledge.routes.upload import router as upload_router


class _User:
    def __init__(self, *, group_ids=None):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = "viewer"
        self.status = "active"
        self.group_id = None
        self.group_ids = list(group_ids or [])


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    def __init__(self, *, accessible_kbs=None):
        self._accessible_kbs = list(accessible_kbs or [])

    def get_group(self, group_id: int):  # noqa: ARG002
        return {
            "can_upload": True,
            "can_review": False,
            "can_download": False,
            "can_copy": False,
            "can_delete": False,
            "can_manage_kb_directory": False,
            "can_view_kb_config": False,
            "can_view_tools": False,
            "accessible_kbs": list(self._accessible_kbs),
            "accessible_kb_nodes": [],
            "accessible_chats": [],
        }


class _RagflowService:
    def get_dataset_index(self):
        return {
            "by_id": {"ds_1": "KB-1", "ds_2": "KB-2"},
            "by_name": {"KB-1": "ds_1", "KB-2": "ds_2"},
        }

    def normalize_dataset_id(self, dataset_ref: str):
        if dataset_ref in {"ds_1", "KB-1"}:
            return "ds_1"
        if dataset_ref in {"ds_2", "KB-2"}:
            return "ds_2"
        return dataset_ref

    def resolve_dataset_name(self, dataset_ref: str):
        if dataset_ref in {"ds_1", "KB-1"}:
            return "KB-1"
        if dataset_ref in {"ds_2", "KB-2"}:
            return "KB-2"
        return dataset_ref


class _OperationApprovalService:
    def __init__(self):
        self.calls = []

    async def create_request(self, *, operation_type, ctx, upload_file, kb_ref):
        content = await upload_file.read()
        self.calls.append(
            {
                "operation_type": operation_type,
                "actor": ctx.payload.sub,
                "kb_ref": kb_ref,
                "filename": upload_file.filename,
                "content": content,
            }
        )
        return {
            "request_id": "req-1",
            "operation_type": operation_type,
            "operation_label": "knowledge_file_upload",
            "status": "in_approval",
            "current_step_no": 1,
            "current_step_name": "review",
            "submitted_at_ms": 1,
            "target_ref": kb_ref,
            "target_label": upload_file.filename,
            "applicant_user_id": ctx.payload.sub,
            "applicant_username": "u1",
            "summary": {"filename": upload_file.filename},
            "last_error": None,
        }


class _Deps:
    def __init__(self, *, accessible_kbs=None):
        user = _User(group_ids=[1])
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore(accessible_kbs=accessible_kbs)
        self.ragflow_service = _RagflowService()
        self.operation_approval_service = _OperationApprovalService()


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


def _make_client(*, accessible_kbs=None) -> tuple[TestClient, _Deps]:
    deps = _Deps(accessible_kbs=accessible_kbs or ["KB-1"])
    app = FastAPI()
    app.state.deps = deps
    app.include_router(upload_router, prefix="/api/knowledge")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
    return TestClient(app), deps


class TestKnowledgeUploadRoutePermissionsUnit(unittest.TestCase):
    def test_upload_requires_explicit_kb_id(self):
        client, deps = _make_client(accessible_kbs=["KB-1"])
        with client:
            resp = client.post(
                "/api/knowledge/upload",
                files={"file": ("demo.txt", b"hello", "text/plain")},
            )

        self.assertEqual(resp.status_code, 400, resp.text)
        self.assertEqual(resp.json().get("detail"), "missing_kb_id")
        self.assertEqual(deps.operation_approval_service.calls, [])

    def test_upload_accepts_dataset_id_variant_when_group_scope_stores_name(self):
        client, deps = _make_client(accessible_kbs=["KB-1"])
        with client:
            resp = client.post(
                "/api/knowledge/upload?kb_id=ds_1",
                files={"file": ("demo.txt", b"hello", "text/plain")},
            )

        self.assertEqual(resp.status_code, 202, resp.text)
        self.assertEqual(resp.json()["request"]["request_id"], "req-1")
        self.assertEqual(
            deps.operation_approval_service.calls,
            [
                {
                    "operation_type": "knowledge_file_upload",
                    "actor": "u1",
                    "kb_ref": "ds_1",
                    "filename": "demo.txt",
                    "content": b"hello",
                }
            ],
        )

    def test_upload_rejects_unknown_dataset_variant(self):
        client, deps = _make_client(accessible_kbs=["KB-1"])
        with client:
            resp = client.post(
                "/api/knowledge/upload?kb_id=ds_2",
                files={"file": ("demo.txt", b"hello", "text/plain")},
            )

        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertEqual(resp.json().get("detail"), "kb_not_allowed")
        self.assertEqual(deps.operation_approval_service.calls, [])


if __name__ == "__main__":
    unittest.main()
