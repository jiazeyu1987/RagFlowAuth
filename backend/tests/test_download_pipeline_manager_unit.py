import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from backend.services.download_pipeline import DownloadPipelineManager


@dataclass
class _Candidate:
    source: str
    source_label: str
    patent_id: str
    title: str
    abstract_text: str
    publication_number: str
    publication_date: str
    inventor: str
    assignee: str
    detail_url: str
    pdf_url: str | None


@dataclass
class _CreatedItem:
    item_id: int
    session_id: str
    status: str
    error: str | None
    source: str
    analysis_text: str | None = None


class _Reusable:
    file_path = __file__
    filename = "cached.pdf"
    file_size = 123
    mime_type = "application/pdf"
    analysis_text = "cached-analysis"
    analysis_file_path = None


class _Provider:
    def __init__(self, items):
        self.items = items

    def search(self, *, query, limit):  # noqa: ARG002
        return self.items


class _Store:
    def __init__(self, reusable=None):
        self.reusable = reusable
        self.runtime_updates = []
        self.created_rows = []
        self.analysis_updates = []

    def update_session_runtime(self, **kwargs):
        self.runtime_updates.append(kwargs)

    def find_reusable_download(self, **kwargs):  # noqa: ARG002
        return self.reusable

    def create_item(self, *, session_id, item):
        self.created_rows.append(item)
        return _CreatedItem(
            item_id=len(self.created_rows),
            session_id=session_id,
            status=item["status"],
            error=item.get("error"),
            source=item["source"],
            analysis_text=item.get("analysis_text"),
        )

    def update_item_analysis(self, **kwargs):
        self.analysis_updates.append(kwargs)
        return None


class _Owner:
    def __init__(self, store, providers):
        self.store = store
        self._sources = providers
        self.finished = []
        self.cancelled = False
        self.stopped = False

    def _build_source_stats(self, enabled, cfg):
        return {
            key: {
                "requested_limit": int(cfg.get(key, {}).get("limit", 10) or 10),
                "candidates": 0,
                "downloaded": 0,
                "reused": 0,
                "failed": 0,
                "skipped_keyword": 0,
                "skipped_duplicate": 0,
                "skipped_stopped": 0,
                "failed_reasons": {},
            }
            for key in enabled
        }

    def _is_cancelled(self, session_id):  # noqa: ARG002
        return self.cancelled

    def _is_stop_requested(self, session_id):  # noqa: ARG002
        return self.stopped

    def _finish_job(self, session_id):
        self.finished.append(session_id)

    @staticmethod
    def _item_key(candidate):
        return candidate.patent_id

    @staticmethod
    def _strip_html(text):
        return str(text or "")

    @staticmethod
    def _is_downloaded_status(status):
        return status in {"downloaded", "downloaded_cached"}


class TestDownloadPipelineManagerUnit(unittest.TestCase):
    def test_run_job_processes_candidates_and_analysis(self):
        store = _Store()
        owner = _Owner(
            store=store,
            providers={
                "google_patents": _Provider(
                    [
                        _Candidate("google_patents", "Google", "p1", "alpha", "abs", "n1", "2026-01-01", "i1", "a1", "u1", "pdf1"),
                        _Candidate("google_patents", "Google", "p2", "skip", "abs", "n2", "2026-01-02", "i2", "a2", "u2", None),
                    ]
                )
            },
        )

        def _candidate_matches(source_key, candidate, keywords, use_and):  # noqa: ARG001
            return candidate.title != "skip"

        def _build_reused_row(source_key, source_index, candidate, reused):  # noqa: ARG001
            return {"status": "downloaded_cached", "source": candidate.source}

        def _build_item_row(source_key, source_index, candidate, session_dir):  # noqa: ARG001
            return {
                "source": candidate.source,
                "status": "downloaded" if candidate.pdf_url else "failed",
                "error": None if candidate.pdf_url else "missing_pdf_url",
            }

        def _maybe_auto_analyze(actor, item, auto_analyze):  # noqa: ARG001
            if not auto_analyze:
                return False, None, None
            return True, "analysis-result", "analysis.txt"

        mgr = DownloadPipelineManager()
        with tempfile.TemporaryDirectory() as temp_dir:
            mgr.run_job(
                owner=owner,
                session_id="s1",
                actor="u1",
                query="q1",
                keywords=["alpha"],
                use_and=True,
                source_queries={"google_patents": "q1"},
                source_errors_seed={},
                auto_analyze=True,
                enabled_sources=["google_patents"],
                source_cfg={"google_patents": {"enabled": True, "limit": 10}},
                candidate_type=_Candidate,
                source_error_type=RuntimeError,
                session_dir=Path(temp_dir),
                source_default_limit=10,
                candidate_matches=_candidate_matches,
                build_reused_row=_build_reused_row,
                build_item_row=_build_item_row,
                maybe_auto_analyze=_maybe_auto_analyze,
                analysis_failure_text=lambda exc: f"auto_analyze_failed: {exc}",
            )

        self.assertEqual(owner.finished, ["s1"])
        self.assertEqual(len(store.created_rows), 1)
        self.assertEqual(store.analysis_updates[0]["analysis_text"], "analysis-result")
        self.assertEqual(store.runtime_updates[-1]["status"], "completed")
        self.assertEqual(store.runtime_updates[-1]["source_stats"]["google_patents"]["skipped_keyword"], 1)

    def test_run_job_reuses_cached_file_and_marks_stopped(self):
        store = _Store(reusable=_Reusable())
        owner = _Owner(
            store=store,
            providers={"google_patents": _Provider([_Candidate("google_patents", "Google", "p1", "alpha", "abs", "n1", "", "", "", "", "pdf1")])},
        )
        owner.stopped = True

        mgr = DownloadPipelineManager()
        with tempfile.TemporaryDirectory() as temp_dir:
            mgr.run_job(
                owner=owner,
                session_id="s2",
                actor="u1",
                query="q1",
                keywords=["alpha"],
                use_and=True,
                source_queries={"google_patents": "q1"},
                source_errors_seed={},
                auto_analyze=False,
                enabled_sources=["google_patents"],
                source_cfg={"google_patents": {"enabled": True, "limit": 10}},
                candidate_type=_Candidate,
                source_error_type=RuntimeError,
                session_dir=Path(temp_dir),
                source_default_limit=10,
                candidate_matches=lambda *args, **kwargs: True,
                build_reused_row=lambda *args, **kwargs: {"source": "google_patents", "status": "downloaded_cached"},
                build_item_row=lambda *args, **kwargs: {"source": "google_patents", "status": "downloaded", "error": None},
                maybe_auto_analyze=lambda *args, **kwargs: (False, None, None),
                analysis_failure_text=lambda exc: f"auto_analyze_failed: {exc}",
            )

        self.assertEqual(owner.finished, ["s2"])
        self.assertEqual(store.runtime_updates[-1]["status"], "stopped")


if __name__ == "__main__":
    unittest.main()
