from __future__ import annotations

import os
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from backend.database.schema.ensure import ensure_schema
from backend.services.kb import KbStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestKbDocumentStorageMigrationUnit(unittest.TestCase):
    def test_ensure_schema_rewrites_absolute_kb_document_paths_to_relative_storage(self):
        td = make_temp_dir(prefix="ragflowauth_kb_doc_storage_migration")
        try:
            repo_root = td / "repo"
            uploads_root = repo_root / "data" / "uploads" / "doc-1"
            uploads_root.mkdir(parents=True, exist_ok=True)
            stored_file = uploads_root / "系统详细设计.md"
            stored_file.write_text("content", encoding="utf-8")

            db_path = repo_root / "data" / "auth.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)

            with mock.patch("backend.app.core.managed_paths.repo_root", return_value=repo_root):
                ensure_schema(db_path)

                conn = sqlite3.connect(db_path)
                try:
                    conn.execute(
                        """
                        INSERT INTO kb_documents (
                            doc_id, filename, file_path, file_size, mime_type,
                            uploaded_by, status, uploaded_at_ms, kb_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "doc-1",
                            stored_file.name,
                            str(stored_file),
                            stored_file.stat().st_size,
                            "text/markdown",
                            "uploader-1",
                            "approved",
                            123,
                            "kb-a",
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()

                ensure_schema(db_path)

                conn = sqlite3.connect(db_path)
                try:
                    migrated_row = conn.execute(
                        "SELECT file_path FROM kb_documents WHERE doc_id = ?",
                        ("doc-1",),
                    ).fetchone()
                finally:
                    conn.close()
                self.assertIsNotNone(migrated_row)
                self.assertEqual(migrated_row[0], "data/uploads/doc-1/系统详细设计.md")

                docs = KbStore(db_path=str(db_path)).list_documents(limit=10)
                self.assertEqual(len(docs), 1)
                self.assertEqual(Path(docs[0].file_path), stored_file)
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
