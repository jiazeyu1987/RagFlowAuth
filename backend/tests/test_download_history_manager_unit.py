import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from backend.services.download_history import DownloadHistoryManager


@dataclass(frozen=True)
class _Session:
    session_id: str
    created_by: str
    created_at_ms: int
    keyword_text: str


@dataclass(frozen=True)
class _Item:
    item_id: int
    session_id: str
    created_at_ms: int
    status: str
    added_doc_id: str | None
    analysis_text: str | None


class _Store:
    def list_sessions_by_creator(self, *, created_by: str, limit: int = 1000):  # noqa: ARG002
        return [
            _Session(session_id="s1", created_by="u1", created_at_ms=10, keyword_text="foo"),
            _Session(session_id="s2", created_by="u1", created_at_ms=20, keyword_text="foo"),
        ]

    def list_items(self, *, session_id: str):
        if session_id == "s1":
            return [_Item(item_id=1, session_id="s1", created_at_ms=10, status="downloaded", added_doc_id=None, analysis_text="ok")]
        return [_Item(item_id=1, session_id="s2", created_at_ms=20, status="downloaded", added_doc_id="doc-1", analysis_text="ok")]


class _Owner:
    def __init__(self):
        self.store = _Store()
        self.deleted = []
        self.added = []

    @staticmethod
    def _history_group_from_session(session):
        return ("and::foo", ["foo"], True)

    @staticmethod
    def _history_item_key(item):
        return str(item.item_id)

    @staticmethod
    def _serialize_item(item):
        return {"item_id": item.item_id, "session_id": item.session_id}

    @staticmethod
    def _is_downloaded_status(status):
        return status == "downloaded"

    @staticmethod
    def _has_effective_analysis_text(text):
        return bool(text)

    def delete_session(self, *, session_id: str, ctx, delete_local_kb: bool):  # noqa: ARG002
        self.deleted.append((session_id, delete_local_kb))
        return {"deleted_items": 1, "deleted_files": 1}

    def add_item_to_local_kb(self, *, session_id: str, item_id: int, ctx, kb_ref: str, from_batch: bool):  # noqa: ARG002
        self.added.append((session_id, item_id, kb_ref, from_batch))
        return {"ok": True}


class TestDownloadHistoryManagerUnit(unittest.TestCase):
    def setUp(self):
        self.owner = _Owner()
        self.mgr = DownloadHistoryManager(owner=self.owner)
        self.ctx = SimpleNamespace(payload=SimpleNamespace(sub="u1"))

    def test_list_and_group_payload(self):
        data = self.mgr.list_history_keywords(ctx=self.ctx)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["history"][0]["downloaded_count"], 1)
        self.assertEqual(data["history"][0]["added_count"], 1)

        payload = self.mgr.get_history_group_payload(history_key="and::foo", ctx=self.ctx)
        self.assertEqual(payload["history"]["session_count"], 2)
        self.assertEqual(payload["summary"]["downloaded"], 1)

    def test_delete_and_add_history_group(self):
        deleted = self.mgr.delete_history_group(history_key="and::foo", ctx=self.ctx)
        self.assertEqual(deleted["deleted_sessions"], 2)
        self.assertEqual(len(self.owner.deleted), 2)

        added = self.mgr.add_history_group_to_local_kb(history_key="and::foo", ctx=self.ctx, kb_ref="[本地论文]")
        self.assertEqual(added["success"], 0)
        self.assertEqual(added["skipped"], 1)


if __name__ == "__main__":
    unittest.main()
