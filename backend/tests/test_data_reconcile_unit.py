from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from backend.services.data_reconcile import DataReconcileService


class DataReconcileServiceUnitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.repo_root = Path(self._tmp.name) / "repo"
        self.data_root = self.repo_root / "data"
        self.uploads_root = self.data_root / "uploads"
        self.paper_root = self.data_root / "paper_downloads"
        self.package_root = self.data_root / "package_drawing_images"
        self.uploads_root.mkdir(parents=True, exist_ok=True)
        self.paper_root.mkdir(parents=True, exist_ok=True)
        self.package_root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_root / "auth.db"
        self._init_db()

    def tearDown(self):
        self._tmp.cleanup()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE kb_documents (
                    doc_id TEXT PRIMARY KEY,
                    file_path TEXT,
                    archive_manifest_path TEXT,
                    archive_package_path TEXT
                );

                CREATE TABLE paper_download_items (
                    item_id INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    file_path TEXT,
                    analysis_file_path TEXT,
                    added_doc_id TEXT,
                    added_analysis_doc_id TEXT,
                    ragflow_doc_id TEXT
                );

                CREATE TABLE package_drawing_images (
                    image_id TEXT PRIMARY KEY,
                    source_type TEXT,
                    rel_path TEXT
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _service(self) -> DataReconcileService:
        return DataReconcileService(db_path=self.db_path)

    def _patched_repo(self):
        stack = ExitStack()
        stack.enter_context(mock.patch("backend.app.core.managed_paths.repo_root", return_value=self.repo_root))
        stack.enter_context(mock.patch("backend.services.data_reconcile.repo_root", return_value=self.repo_root))
        return stack

    def test_report_rewrites_legacy_kb_paths_and_reports_invalid_paths(self):
        legacy_file = self.uploads_root / "legacy.txt"
        legacy_file.write_text("legacy", encoding="utf-8")
        orphan_file = self.uploads_root / "orphan.txt"
        orphan_file.write_text("orphan", encoding="utf-8")

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO kb_documents (doc_id, file_path, archive_manifest_path, archive_package_path)
                VALUES (?, ?, ?, ?)
                """,
                ("doc-1", "/app/data/uploads/legacy.txt", None, None),
            )
            conn.execute(
                """
                INSERT INTO kb_documents (doc_id, file_path, archive_manifest_path, archive_package_path)
                VALUES (?, ?, ?, ?)
                """,
                ("doc-2", "C:/outside/rogue.txt", None, None),
            )
            conn.commit()
        finally:
            conn.close()

        with self._patched_repo():
            report = self._service().report()

        self.assertEqual(
            [
                action.values
                for action in report.db_updates
                if action.table == "kb_documents"
            ],
            [{"file_path": "data/uploads/legacy.txt"}],
        )
        invalid_issue = next(
            issue for issue in report.issues if issue.row_ref == {"doc_id": "doc-2"}
        )
        self.assertEqual(invalid_issue.reason, "invalid_managed_data_path")
        self.assertIn(str(orphan_file.resolve()), [item.path for item in report.file_deletes])
        self.assertNotIn(str(legacy_file.resolve()), [item.path for item in report.file_deletes])

    def test_apply_deletes_only_regenerable_download_rows_and_orphan_runtime_files(self):
        kept_file = self.paper_root / "kept.pdf"
        kept_file.write_text("keep", encoding="utf-8")
        orphan_file = self.paper_root / "orphan.pdf"
        orphan_file.write_text("orphan", encoding="utf-8")
        empty_dir = self.paper_root / "empty"
        empty_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO paper_download_items (
                    item_id, session_id, file_path, analysis_file_path,
                    added_doc_id, added_analysis_doc_id, ragflow_doc_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (1, "sess-a", "data/paper_downloads/missing.pdf", None, None, None, None),
            )
            conn.execute(
                """
                INSERT INTO paper_download_items (
                    item_id, session_id, file_path, analysis_file_path,
                    added_doc_id, added_analysis_doc_id, ragflow_doc_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (2, "sess-b", "data/paper_downloads/kept.pdf", None, None, None, None),
            )
            conn.execute(
                """
                INSERT INTO paper_download_items (
                    item_id, session_id, file_path, analysis_file_path,
                    added_doc_id, added_analysis_doc_id, ragflow_doc_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (3, "sess-c", "data/paper_downloads/missing-linked.pdf", None, "doc-1", None, None),
            )
            conn.commit()
        finally:
            conn.close()

        with self._patched_repo():
            payload = self._service().apply()

        self.assertEqual(payload["summary"]["db_deletes"], 1)
        self.assertFalse(orphan_file.exists())
        self.assertFalse(empty_dir.exists())
        self.assertTrue(kept_file.exists())

        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT item_id FROM paper_download_items ORDER BY item_id"
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual([row[0] for row in rows], [2, 3])

    def test_report_rewrites_legacy_package_drawing_relative_paths(self):
        image_file = self.package_root / "nested" / "drawing.png"
        image_file.parent.mkdir(parents=True, exist_ok=True)
        image_file.write_bytes(b"png")

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO package_drawing_images (image_id, source_type, rel_path)
                VALUES (?, ?, ?)
                """,
                ("img-1", "embedded", "/app/data/package_drawing_images/nested/drawing.png"),
            )
            conn.commit()
        finally:
            conn.close()

        with self._patched_repo():
            report = self._service().report()

        self.assertEqual(
            [
                action.values
                for action in report.db_updates
                if action.table == "package_drawing_images"
            ],
            [{"rel_path": "nested/drawing.png"}],
        )


if __name__ == "__main__":
    unittest.main()
