import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.review.router import router as review_router
from backend.database.schema.ensure import ensure_schema
from backend.services.kb import KbStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def __init__(self, user):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user

    def get_usernames_by_ids(self, user_ids):  # noqa: ARG002
        return {}


class _PermissionGroupStore:
    def __init__(self, groups: dict[int, dict]):
        self._groups = groups

    def get_group(self, group_id: int):
        return self._groups.get(int(group_id))


class _Deps:
    def __init__(self, *, user, kb_store):
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore(
            {
                101: {
                    "can_review": True,
                    "can_upload": False,
                    "can_download": False,
                    "can_copy": False,
                    "can_delete": False,
                    "can_manage_kb_directory": False,
                    "can_view_kb_config": False,
                    "can_view_tools": False,
                    "accessible_kbs": ["kb-a"],
                    "accessible_chats": [],
                    "accessible_tools": [],
                }
            }
        )
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = kb_store


class TestReviewWorkflowApiUnit(unittest.TestCase):
    def _build_app(self, *, user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(review_router, prefix="/api/knowledge")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_put_and_get_workflow_with_assignment_fields(self):
        td = make_temp_dir(prefix="ragflowauth_workflow_api_admin")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            kb_store = KbStore(db_path=db_path)
            admin_user = SimpleNamespace(
                user_id="admin-1",
                username="admin1",
                email="admin1@example.com",
                role="admin",
                status="active",
                group_id=None,
                group_ids=[],
                company_id=1,
                department_id=1,
            )

            app = self._build_app(user_id="admin-1", deps=_Deps(user=admin_user, kb_store=kb_store))

            with TestClient(app) as client:
                put_resp = client.put(
                    "/api/knowledge/review/workflows/wf-kb-a",
                    json={
                        "kb_ref": "kb-a",
                        "name": "KB-A Workflow",
                        "steps": [
                            {
                                "step_no": 1,
                                "step_name": "L1",
                                "approver_user_id": "reviewer-a",
                            },
                            {
                                "step_no": 2,
                                "step_name": "L2",
                                "approver_role": "reviewer",
                                "approver_company_id": 1,
                                "approval_mode": "all",
                            },
                        ],
                    },
                )
                self.assertEqual(put_resp.status_code, 200, put_resp.text)
                self.assertEqual(put_resp.json().get("workflow_id"), "wf-kb-a")
                self.assertEqual(put_resp.json()["steps"][0]["approver_user_id"], "reviewer-a")

                get_resp = client.get("/api/knowledge/review/workflows?kb_ref=kb-a")
                self.assertEqual(get_resp.status_code, 200, get_resp.text)
                data = get_resp.json()
                self.assertEqual(data.get("count"), 1)
                self.assertEqual(data["items"][0]["steps"][1]["approver_role"], "reviewer")
                self.assertEqual(data["items"][0]["steps"][1]["approver_company_id"], 1)
        finally:
            cleanup_dir(td)

    def test_pending_approvals_endpoint_returns_only_docs_for_current_user(self):
        td = make_temp_dir(prefix="ragflowauth_workflow_api_reviewer")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            kb_store = KbStore(db_path=db_path)
            file_path = Path(td) / "doc.txt"
            file_path.write_text("pending", encoding="utf-8")
            kb_store.create_document(
                filename="assigned.txt",
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )
            kb_store.create_document(
                filename="not-assigned.txt",
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                mime_type="text/plain",
                uploaded_by="uploader-1",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
                status="pending",
            )

            admin_user = SimpleNamespace(
                user_id="admin-1",
                username="admin1",
                email="admin1@example.com",
                role="admin",
                status="active",
                group_id=None,
                group_ids=[],
                company_id=1,
                department_id=1,
            )
            admin_app = self._build_app(user_id="admin-1", deps=_Deps(user=admin_user, kb_store=kb_store))
            with TestClient(admin_app) as admin_client:
                put_resp = admin_client.put(
                    "/api/knowledge/review/workflows/wf-kb-a",
                    json={
                        "kb_ref": "kb-a",
                        "name": "KB-A Workflow",
                        "steps": [
                            {"step_no": 1, "step_name": "L1", "approver_user_id": "reviewer-a"},
                            {"step_no": 2, "step_name": "L2", "approver_user_id": "reviewer-b"},
                        ],
                    },
                )
                self.assertEqual(put_resp.status_code, 200, put_resp.text)

            reviewer_user = SimpleNamespace(
                user_id="reviewer-a",
                username="reviewer_a",
                email="reviewer-a@example.com",
                role="reviewer",
                status="active",
                group_id=None,
                group_ids=[101],
                company_id=1,
                department_id=10,
            )
            app = self._build_app(user_id="reviewer-a", deps=_Deps(user=reviewer_user, kb_store=kb_store))

            with TestClient(app) as client:
                resp = client.get("/api/knowledge/review/pending-approvals")
                self.assertEqual(resp.status_code, 200, resp.text)
                data = resp.json()
                self.assertEqual(data["count"], 2)
                self.assertTrue(all(item["current_step_no"] == 1 for item in data["items"]))
                self.assertTrue(all(item["current_step_name"] == "L1" for item in data["items"]))
        finally:
            cleanup_dir(td)
