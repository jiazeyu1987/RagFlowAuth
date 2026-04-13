import asyncio
import os
import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.agents.router import router as agents_router
from backend.app.modules.chat.router import router as chat_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self, role: str = "admin"):
        self.user_id = "u-admin"
        self.username = "admin1"
        self.email = "admin1@example.com"
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


class _FakeRagflowService:
    def list_datasets(self):
        return [{"id": "ds-1", "name": "KB 1"}]

    def resolve_dataset_name(self, dataset_ref: str):
        if dataset_ref in {"ds-1", "KB 1"}:
            return "KB 1"
        return dataset_ref

    def get_document_detail(self, doc_id: str, dataset_name: str | None = None):  # noqa: ARG002
        return {"name": "Spec.pdf"} if doc_id == "doc-1" else None


class _FakeChatMessageSourcesStore:
    def __init__(self):
        self.upsert_calls = []

    def upsert_sources(self, *, chat_id: str, session_id: str, assistant_text: str, sources: list[dict]):
        self.upsert_calls.append(
            {
                "chat_id": chat_id,
                "session_id": session_id,
                "assistant_text": assistant_text,
                "sources": sources,
            }
        )


class _FakeRagflowChatService:
    def __init__(self):
        self.retrieve_calls = []
        self.chat_calls = []

    def retrieve_chunks(
        self,
        *,
        question: str,
        dataset_ids: list[str],
        page: int = 1,
        page_size: int = 30,
        similarity_threshold: float = 0.2,
        top_k: int = 30,
        keyword: bool = False,
        highlight: bool = False,
    ):
        self.retrieve_calls.append(
            {
                "question": question,
                "dataset_ids": list(dataset_ids),
                "page": page,
                "page_size": page_size,
                "similarity_threshold": similarity_threshold,
                "top_k": top_k,
                "keyword": keyword,
                "highlight": highlight,
            }
        )
        return {
            "chunks": [
                {
                    "document_id": "doc-1",
                    "dataset": "KB 1",
                    "filename": "Spec.pdf",
                    "content": "quality clause 1",
                }
            ],
            "total": 1,
            "page": page,
            "page_size": page_size,
        }

    async def chat(
        self,
        *,
        chat_id: str,
        question: str,
        stream: bool,
        session_id: str | None,
        user_id: str,
        trace_id: str,
    ):
        self.chat_calls.append(
            {
                "chat_id": chat_id,
                "question": question,
                "stream": stream,
                "session_id": session_id,
                "user_id": user_id,
                "trace_id": trace_id,
            }
        )
        yield {
            "code": 0,
            "data": {
                "session_id": session_id or "session-1",
                "answer": "Answer using Spec.pdf",
            },
        }
        await asyncio.sleep(0)


class _Deps:
    def __init__(self, *, user: _User, db_path: str, with_audit: bool = True):
        self.user_store = _UserStore(user)
        self.permission_group_store = _PermissionGroupStore()
        self.ragflow_service = _FakeRagflowService()
        self.ragflow_chat_service = _FakeRagflowChatService()
        self.chat_message_sources_store = _FakeChatMessageSourcesStore()
        if with_audit:
            self.audit_log_store = AuditLogStore(db_path=db_path)
            self.audit_log_manager = AuditLogManager(store=self.audit_log_store)


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u-admin")


class TestSearchChatAuditUnit(unittest.TestCase):
    def test_search_endpoint_writes_global_search_audit_event(self):
        td = make_temp_dir(prefix="ragflowauth_search_audit")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            app.state.deps = _Deps(user=_User(), db_path=db_path)
            app.include_router(agents_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.post(
                    "/api/search",
                    json={
                        "question": "quality clause",
                        "dataset_ids": ["ds-1"],
                        "page": 1,
                        "page_size": 10,
                        "top_k": 5,
                        "similarity_threshold": 0.3,
                        "keyword": True,
                        "highlight": True,
                    },
                )

            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            self.assertEqual(data["total"], 1)

            events = app.state.deps.audit_log_manager.list_events(action="global_search_execute", limit=10)["items"]
            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event["source"], "global_search")
            self.assertEqual(event["event_type"], "search")
            self.assertEqual(event["before"]["question"], "quality clause")
            self.assertEqual(event["after"]["returned_chunks"], 1)
            self.assertEqual(event["doc_id"], "doc-1")
            self.assertEqual(event["evidence_refs"][0]["filename"], "Spec.pdf")
        finally:
            cleanup_dir(td)

    def test_search_endpoint_fails_when_audit_dependency_is_missing(self):
        td = make_temp_dir(prefix="ragflowauth_search_audit_blocked")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            app.state.deps = _Deps(user=_User(), db_path=db_path, with_audit=False)
            app.include_router(agents_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.post("/api/search", json={"question": "quality clause", "dataset_ids": ["ds-1"]})

            self.assertEqual(resp.status_code, 500, resp.text)
            self.assertEqual(resp.json()["detail"], "search_failed")
        finally:
            cleanup_dir(td)

    def test_chat_completion_writes_smart_chat_audit_event(self):
        td = make_temp_dir(prefix="ragflowauth_chat_audit")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            app.state.deps = _Deps(user=_User(), db_path=db_path)
            app.include_router(chat_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.post(
                    "/api/chats/chat-1/completions",
                    headers={"X-Chat-Trace-Id": "trace-1"},
                    json={"question": "What changed?", "stream": True, "session_id": "session-1"},
                )

            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertIn("Answer using Spec.pdf", resp.text)

            events = app.state.deps.audit_log_manager.list_events(action="smart_chat_completion", limit=10)["items"]
            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event["source"], "smart_chat")
            self.assertEqual(event["resource_type"], "chat_session")
            self.assertEqual(event["resource_id"], "session-1")
            self.assertEqual(event["before"]["question"], "What changed?")
            self.assertEqual(event["meta"]["source_count"], 1)
            self.assertEqual(event["evidence_refs"][0]["resource_id"], "doc-1")
            self.assertEqual(
                app.state.deps.chat_message_sources_store.upsert_calls[0]["session_id"],
                "session-1",
            )
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
