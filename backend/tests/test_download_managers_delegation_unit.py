import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from backend.services.paper_download.manager import PaperDownloadManager
from backend.services.paper_download.models import PaperDownloadSession
from backend.services.patent_download.manager import PatentDownloadManager
from backend.services.patent_download.models import PatentDownloadSession


class _FakeAuditManager:
    def __init__(self):
        self.calls = []

    def safe_log_ctx_event(self, **kwargs):
        self.calls.append(kwargs)


class _FakeLLMManager:
    def __init__(self):
        self.calls = []

    def ask(self, **kwargs):
        self.calls.append(kwargs)
        return "delegated-answer"

    def resolve_general_llm_chat_ids(self):
        return ["chat-1"]

    def get_or_create_session(self, **kwargs):
        self.calls.append({"session": kwargs})
        return "sid-1"


class _FakePipelineManager:
    def __init__(self):
        self.calls = []

    def run_job(self, **kwargs):
        self.calls.append(kwargs)


@dataclass(frozen=True)
class _CommonItem:
    item_id: int
    status: str
    added_doc_id: str | None


class _FakePatentStore:
    def get_session(self, session_id):  # noqa: ARG002
        return PatentDownloadSession(
            session_id="s1",
            created_by="u1",
            created_at_ms=0,
            keyword_text="",
            keywords_json="[]",
            use_and=True,
            sources_json="{}",
            status="completed",
            error=None,
            source_errors_json="[]",
            source_stats_json="{}",
        )

    def list_items(self, session_id):  # noqa: ARG002
        return [_CommonItem(item_id=1, status="downloaded", added_doc_id="doc-1")]


class _FakePaperStore:
    def get_session(self, session_id):  # noqa: ARG002
        return PaperDownloadSession(
            session_id="s1",
            created_by="u1",
            created_at_ms=0,
            keyword_text="",
            keywords_json="[]",
            use_and=True,
            sources_json="{}",
            status="completed",
            error=None,
            source_errors_json="[]",
            source_stats_json="{}",
        )

    def list_items(self, session_id):  # noqa: ARG002
        return [_CommonItem(item_id=1, status="downloaded", added_doc_id="doc-1")]


class TestDownloadManagersDelegationUnit(unittest.TestCase):
    def test_patent_manager_delegates_llm_pipeline_and_audit(self):
        deps = SimpleNamespace(
            patent_download_store=_FakePatentStore(),
            ragflow_chat_service=None,
            audit_log_store=None,
            audit_log_manager=_FakeAuditManager(),
        )
        mgr = PatentDownloadManager(deps)
        mgr._llm_manager = _FakeLLMManager()
        mgr._pipeline_manager = _FakePipelineManager()
        mgr._assert_session_access = lambda session, ctx: None
        self.assertEqual(mgr._source_factory.__class__.__name__, "PatentSourceFactory")
        self.assertEqual(set(mgr._source_registry.build_mapping().keys()), {"google_patents", "uspto"})

        answer = mgr._ask_general_llm(actor="u1", question="q1")
        self.assertEqual(answer, "delegated-answer")

        mgr._run_download_job(
            session_id="s1",
            actor="u1",
            query="q1",
            keywords=["alpha"],
            use_and=True,
            source_queries={"google_patents": "q1"},
            source_errors_seed={},
            auto_analyze=False,
            enabled_sources=["google_patents"],
            source_cfg={"google_patents": {"enabled": True, "limit": 10}},
        )
        self.assertEqual(mgr._pipeline_manager.calls[0]["candidate_type"].__name__, "DownloadCandidate")

        ctx = SimpleNamespace(payload=SimpleNamespace(sub="u1"), snapshot=None, deps=deps)
        result = mgr.add_all_to_local_kb(session_id="s1", ctx=ctx, kb_ref="[鏈湴涓撳埄]")
        self.assertEqual(result["success"], 0)
        self.assertEqual(result["items"][0]["already_added"], True)
        self.assertEqual(deps.audit_log_manager.calls[0]["action"], "patent_kb_add_all")

    def test_paper_manager_delegates_llm_pipeline_and_audit(self):
        deps = SimpleNamespace(
            paper_download_store=_FakePaperStore(),
            ragflow_chat_service=None,
            audit_log_store=None,
            audit_log_manager=_FakeAuditManager(),
        )
        mgr = PaperDownloadManager(deps)
        mgr._llm_manager = _FakeLLMManager()
        mgr._pipeline_manager = _FakePipelineManager()
        mgr._assert_session_access = lambda session, ctx: None
        self.assertEqual(mgr._source_factory.__class__.__name__, "PaperSourceFactory")
        self.assertEqual(set(mgr._source_registry.build_mapping().keys()), {"arxiv", "pubmed", "europe_pmc", "openalex"})

        answer = mgr._ask_general_llm(actor="u1", question="q1")
        self.assertEqual(answer, "delegated-answer")

        mgr._run_download_job(
            session_id="s1",
            actor="u1",
            query="q1",
            keywords=["alpha"],
            use_and=True,
            source_queries={"arxiv": "\"q1\""},
            source_errors_seed={},
            auto_analyze=False,
            enabled_sources=["arxiv"],
            source_cfg={"arxiv": {"enabled": True, "limit": 30}},
        )
        self.assertEqual(mgr._pipeline_manager.calls[0]["candidate_type"].__name__, "DownloadCandidate")

        ctx = SimpleNamespace(payload=SimpleNamespace(sub="u1"), snapshot=None, deps=deps)
        result = mgr.add_all_to_local_kb(session_id="s1", ctx=ctx, kb_ref="[鏈湴璁烘枃]")
        self.assertEqual(result["success"], 0)
        self.assertEqual(result["items"][0]["already_added"], True)
        self.assertEqual(deps.audit_log_manager.calls[0]["action"], "paper_kb_add_all")


if __name__ == "__main__":
    unittest.main()
