import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.operation_approvals.router import router as operation_approval_router


class _FakeUser:
    def __init__(self, *, role: str = "admin", user_id: str = "u1"):
        self.user_id = user_id
        self.username = user_id
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.company_id = 1
        self.department_id = 1


class _FakeUserStore:
    def __init__(self, *, role: str):
        self._role = role

    def get_by_user_id(self, user_id: str):
        return _FakeUser(role=self._role, user_id=user_id)


class _FakePermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _FakeOperationApprovalService:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def list_workflows(self):
        return []

    def upsert_workflow(self, **kwargs):
        self.calls.append(("workflow", dict(kwargs)))
        return {"operation_type": kwargs["operation_type"]}

    def list_requests_for_user(self, **kwargs):  # noqa: ARG002
        return {"items": [], "count": 0}

    def get_request_detail_for_user(self, **kwargs):  # noqa: ARG002
        return {"request_id": "req-1"}

    def get_stats_for_user(self, **kwargs):  # noqa: ARG002
        return {"in_approval_count": 0}

    def approve_request(self, **kwargs):
        self.calls.append(("approve", dict(kwargs)))
        return {"request_id": kwargs["request_id"], "status": "approved"}

    def reject_request(self, **kwargs):
        self.calls.append(("reject", dict(kwargs)))
        return {"request_id": kwargs["request_id"], "status": "rejected"}

    def withdraw_request(self, **kwargs):
        self.calls.append(("withdraw", dict(kwargs)))
        return {"request_id": kwargs["request_id"], "status": "withdrawn"}

    def list_todos_for_user(self, **kwargs):  # noqa: ARG002
        return {"items": [], "count": 0}


class _FakeDeps:
    def __init__(self, *, role: str):
        self.user_store = _FakeUserStore(role=role)
        self.permission_group_store = _FakePermissionGroupStore()
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=":memory:")
        self.operation_approval_service = _FakeOperationApprovalService()


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestOperationApprovalRouterUnit(unittest.TestCase):
    def _make_client(self, *, role: str = "admin") -> tuple[TestClient, _FakeDeps]:
        app = FastAPI()
        deps = _FakeDeps(role=role)
        app.state.deps = deps
        app.include_router(operation_approval_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app), deps

    def test_mutation_routes_return_explicit_result_envelopes(self):
        client, deps = self._make_client()
        with patch("backend.app.modules.operation_approvals.router.assert_user_training_for_action", return_value=None):
            with client:
                workflow_resp = client.put(
                    "/api/operation-approvals/workflows/knowledge_file_upload",
                    json={
                        "name": "demo",
                        "steps": [
                            {
                                "step_name": "review",
                                "members": [{"member_type": "user", "member_ref": "u2"}],
                            }
                        ],
                    },
                )
                approve_resp = client.post(
                    "/api/operation-approvals/requests/req-1/approve",
                    json={
                        "sign_token": "token-1",
                        "signature_meaning": "approve",
                        "signature_reason": "ok",
                        "notes": "ok",
                    },
                )
                reject_resp = client.post(
                    "/api/operation-approvals/requests/req-1/reject",
                    json={
                        "sign_token": "token-2",
                        "signature_meaning": "reject",
                        "signature_reason": "no",
                        "notes": "no",
                    },
                )
                withdraw_resp = client.post(
                    "/api/operation-approvals/requests/req-1/withdraw",
                    json={"reason": "changed"},
                )

        self.assertEqual(workflow_resp.status_code, 200, workflow_resp.text)
        self.assertEqual(
            workflow_resp.json(),
            {
                "result": {
                    "message": "operation_approval_workflow_updated",
                    "operation_type": "knowledge_file_upload",
                }
            },
        )
        self.assertEqual(
            approve_resp.json(),
            {
                "result": {
                    "message": "operation_approval_request_approved",
                    "request_id": "req-1",
                    "status": "approved",
                }
            },
        )
        self.assertEqual(
            reject_resp.json(),
            {
                "result": {
                    "message": "operation_approval_request_rejected",
                    "request_id": "req-1",
                    "status": "rejected",
                }
            },
        )
        self.assertEqual(
            withdraw_resp.json(),
            {
                "result": {
                    "message": "operation_approval_request_withdrawn",
                    "request_id": "req-1",
                    "status": "withdrawn",
                }
            },
        )
        self.assertEqual(
            deps.operation_approval_service.calls,
            [
                (
                    "workflow",
                    {
                        "operation_type": "knowledge_file_upload",
                        "name": "demo",
                        "steps": [{"step_name": "review", "members": [{"member_type": "user", "member_ref": "u2"}]}],
                    },
                ),
                (
                    "approve",
                    {
                        "request_id": "req-1",
                        "actor_user": unittest.mock.ANY,
                        "sign_token": "token-1",
                        "signature_meaning": "approve",
                        "signature_reason": "ok",
                        "notes": "ok",
                    },
                ),
                (
                    "reject",
                    {
                        "request_id": "req-1",
                        "actor_user": unittest.mock.ANY,
                        "sign_token": "token-2",
                        "signature_meaning": "reject",
                        "signature_reason": "no",
                        "notes": "no",
                    },
                ),
                (
                    "withdraw",
                    {
                        "request_id": "req-1",
                        "actor_user": unittest.mock.ANY,
                        "reason": "changed",
                    },
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
