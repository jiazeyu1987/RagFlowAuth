import os
import tempfile
import unittest
import uuid

from backend.database.schema.ensure import ensure_schema
from backend.services.paper_download.store import PaperDownloadStore, item_to_dict as paper_item_to_dict, session_to_dict as paper_session_to_dict
from backend.services.patent_download.store import PatentDownloadStore, item_to_dict as patent_item_to_dict, session_to_dict as patent_session_to_dict


class TestDownloadStoreRefactorUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def _exercise_store(self, *, store, session_to_dict, item_to_dict, actor: str):
        session_id = str(uuid.uuid4())
        session = store.create_session(
            session_id=session_id,
            created_by=actor,
            keyword_text="alpha,beta",
            keywords=["alpha", "beta"],
            use_and=True,
            sources={"s1": {"enabled": True, "limit": 5}},
            status="running",
            source_errors={},
            source_stats={"s1": {"enabled": True, "limit": 5}},
        )
        self.assertEqual(session.session_id, session_id)

        updated_session = store.update_session_runtime(
            session_id=session_id,
            status="completed",
            source_errors={"s1": "none"},
            source_stats={"s1": {"fetched": 1}},
        )
        self.assertIsNotNone(updated_session)
        self.assertEqual(updated_session.status, "completed")

        loaded_session = store.get_session(session_id)
        self.assertIsNotNone(loaded_session)
        payload = session_to_dict(loaded_session)
        self.assertEqual(payload["keywords"], ["alpha", "beta"])
        self.assertEqual(payload["source_errors"], {"s1": "none"})

        item = store.create_item(
            session_id=session_id,
            item={
                "source": "arxiv",
                "source_label": "arxiv",
                "patent_id": "pid-1",
                "title": "title-1",
                "abstract_text": "abstract-1",
                "publication_number": "pub-1",
                "publication_date": "2026-01-01",
                "inventor": "inv-1",
                "assignee": "asg-1",
                "detail_url": "https://example.com/detail",
                "pdf_url": "https://example.com/file.pdf",
                "file_path": "d:/tmp/file.pdf",
                "filename": "file.pdf",
                "file_size": 1234,
                "mime_type": "application/pdf",
                "status": "downloaded",
                "error": None,
                "analysis_text": None,
                "analysis_file_path": None,
                "added_doc_id": None,
                "added_analysis_doc_id": None,
                "ragflow_doc_id": None,
            },
        )
        self.assertEqual(item.session_id, session_id)
        self.assertEqual(item.status, "downloaded")

        listed_items = store.list_items(session_id=session_id)
        self.assertEqual(len(listed_items), 1)

        loaded_item = store.get_item(session_id=session_id, item_id=item.item_id)
        self.assertIsNotNone(loaded_item)

        reusable = store.find_reusable_download(
            created_by=actor,
            patent_id="pid-1",
            publication_number=None,
            title=None,
        )
        self.assertIsNotNone(reusable)
        self.assertEqual(reusable.item_id, item.item_id)

        marked = store.mark_item_added(
            session_id=session_id,
            item_id=item.item_id,
            added_doc_id="doc-1",
            added_analysis_doc_id=None,
            ragflow_doc_id="rf-1",
        )
        self.assertIsNotNone(marked)
        self.assertEqual(marked.added_doc_id, "doc-1")

        analyzed = store.update_item_analysis(
            session_id=session_id,
            item_id=item.item_id,
            analysis_text="analysis-ok",
            analysis_file_path="d:/tmp/file.analysis.txt",
        )
        self.assertIsNotNone(analyzed)
        as_payload = item_to_dict(analyzed)
        self.assertEqual(as_payload["analysis_text"], "analysis-ok")

        sessions = store.list_sessions_by_creator(created_by=actor, limit=10)
        self.assertEqual(len(sessions), 1)

        self.assertTrue(store.delete_item(session_id=session_id, item_id=item.item_id))
        del_res = store.delete_session(session_id=session_id)
        self.assertEqual(del_res["deleted_items"], 0)
        self.assertIsNone(store.get_session(session_id))

    def test_paper_store_behaves_like_patent_store(self):
        self._exercise_store(
            store=PaperDownloadStore(db_path=self.db_path),
            session_to_dict=paper_session_to_dict,
            item_to_dict=paper_item_to_dict,
            actor="u-paper",
        )
        self._exercise_store(
            store=PatentDownloadStore(db_path=self.db_path),
            session_to_dict=patent_session_to_dict,
            item_to_dict=patent_item_to_dict,
            actor="u-patent",
        )


if __name__ == "__main__":
    unittest.main()
