import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.services.download_kb_lifecycle import DownloadKbLifecycleManager


@dataclass(frozen=True)
class _Item:
    item_id: int
    session_id: str
    patent_id: str | None
    source: str
    status: str
    file_path: str | None
    filename: str | None
    mime_type: str | None
    analysis_file_path: str | None
    added_doc_id: str | None
    added_analysis_doc_id: str | None


@dataclass(frozen=True)
class _Session:
    session_id: str
    created_by: str


class _Store:
    def __init__(self, item):
        self._item = item

    def mark_item_added(self, **kwargs):  # noqa: ARG002
        return self._item

    def get_session(self, session_id):  # noqa: ARG002
        return _Session(session_id="s1", created_by="u1")

    def list_items(self, session_id):  # noqa: ARG002
        return [self._item]

    def delete_item(self, **kwargs):  # noqa: ARG002
        return True

    def delete_session(self, **kwargs):  # noqa: ARG002
        return {"deleted_items": 1}


class _KbStore:
    def get_document(self, doc_id):  # noqa: ARG002
        return None


class _Audit:
    def __init__(self):
        self.calls = []

    def safe_log_ctx_event(self, **kwargs):
        self.calls.append(kwargs)


class _Owner:
    _MIME_TYPE_DEFAULT = "application/pdf"

    def __init__(self, tmpdir: str, item):
        self.deps = SimpleNamespace(kb_store=_KbStore())
        self.store = _Store(item)
        self._audit_manager = _Audit()
        self._tmpdir = Path(tmpdir)
        self._item = item
        self.cancelled = []
        self.finished = []

    def _resolve_session_and_item(self, **kwargs):  # noqa: ARG002
        return _Session(session_id="s1", created_by="u1"), self._item

    @staticmethod
    def _is_downloaded_status(status):
        return status == "downloaded"

    def _serialize_item(self, item):
        return {"item_id": item.item_id}

    def _ensure_file_bytes(self, **kwargs):  # noqa: ARG002
        return b"pdf"

    def _upload_blob_to_kb(self, **kwargs):  # noqa: ARG002
        return SimpleNamespace(
            doc_id="doc-1",
            filename="x.pdf",
            kb_id="kb1",
            kb_name="kb1",
            ragflow_doc_id="rf-1",
            status="approved",
            kb_dataset_id=None,
        )

    def get_session_payload(self, **kwargs):  # noqa: ARG002
        return {"session_id": "s1"}

    def _assert_session_access(self, session, ctx):  # noqa: ARG002
        return None

    def _cancel_job(self, session_id):
        self.cancelled.append(session_id)
        return None

    def _finish_job(self, session_id):
        self.finished.append(session_id)

    def _download_root(self):
        return self._tmpdir


class TestDownloadKbLifecycleManagerUnit(unittest.TestCase):
    def test_add_all_and_delete_session(self):
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "x.pdf"
            file_path.write_bytes(b"pdf")
            item = _Item(
                item_id=1,
                session_id="s1",
                patent_id="p1",
                source="arxiv",
                status="downloaded",
                file_path=str(file_path),
                filename="x.pdf",
                mime_type="application/pdf",
                analysis_file_path=None,
                added_doc_id=None,
                added_analysis_doc_id=None,
            )
            owner = _Owner(td, item)
            mgr = DownloadKbLifecycleManager(owner=owner)
            ctx = SimpleNamespace(
                payload=SimpleNamespace(sub="u1"),
                snapshot=PermissionSnapshot(
                    is_admin=True,
                    can_upload=True,
                    can_review=True,
                    can_download=True,
                    can_delete=True,
                    can_manage_kb_directory=True,
                    can_view_kb_config=True,
                    can_view_tools=True,
                    kb_scope=ResourceScope.ALL,
                    kb_names=frozenset(),
                    chat_scope=ResourceScope.NONE,
                    chat_ids=frozenset(),
                ),
            )

            add_res = mgr.add_all_to_local_kb(
                session_id="s1",
                ctx=ctx,
                kb_ref="[本地论文]",
                session_not_found_detail="paper_session_not_found",
                action_name="paper_kb_add_all",
                source_name="paper_download",
                item_add_fn=lambda **kwargs: mgr.add_item_to_local_kb(
                    **kwargs,
                    action_name="paper_kb_add",
                    source_name="paper_download",
                    entity_source_key="paper_source",
                    entity_id_key="paper_id",
                    default_filename_prefix="paper",
                    add_review_notes="added_from_paper_download",
                    analysis_review_notes="added_paper_analysis_from_paper_download",
                ),
            )
            self.assertEqual(add_res["success"], 1)

            del_res = mgr.delete_session(
                session_id="s1",
                ctx=ctx,
                delete_local_kb=False,
                session_not_found_detail="paper_session_not_found",
                action_name="paper_session_delete",
                source_name="paper_download",
            )
            self.assertEqual(del_res["deleted_items"], 1)
            self.assertIn("s1", owner.finished)


if __name__ == "__main__":
    unittest.main()
