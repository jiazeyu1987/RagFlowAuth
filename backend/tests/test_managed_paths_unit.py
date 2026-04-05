from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend.app.core import managed_paths


class ManagedPathsUnitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.repo_root = Path(self._tmp.name) / "repo"
        (self.repo_root / "data" / "uploads").mkdir(parents=True, exist_ok=True)
        self._repo_patch = mock.patch.object(managed_paths, "repo_root", return_value=self.repo_root)
        self._repo_patch.start()

    def tearDown(self):
        self._repo_patch.stop()
        self._tmp.cleanup()

    def test_to_managed_data_storage_path_normalizes_absolute_repo_data_path(self):
        absolute = self.repo_root / "data" / "uploads" / "demo.txt"
        self.assertEqual(
            managed_paths.to_managed_data_storage_path(absolute, field_name="kb_documents.file_path"),
            "data/uploads/demo.txt",
        )

    def test_resolve_managed_data_storage_path_rejects_absolute_stored_values(self):
        absolute = self.repo_root / "data" / "uploads" / "demo.txt"
        with self.assertRaises(ValueError) as cm:
            managed_paths.resolve_managed_data_storage_path(
                absolute,
                field_name="kb_documents.file_path",
            )

        self.assertIn("stored_path_must_be_relative", str(cm.exception))

    def test_to_managed_child_storage_path_normalizes_within_managed_root(self):
        image_root = self.repo_root / "data" / "package_drawing_images"
        image_root.mkdir(parents=True, exist_ok=True)
        absolute = image_root / "nested" / "image.png"
        absolute.parent.mkdir(parents=True, exist_ok=True)

        self.assertEqual(
            managed_paths.to_managed_child_storage_path(
                absolute,
                managed_root=image_root,
                field_name="package_drawing_images.rel_path",
            ),
            "nested/image.png",
        )

    def test_to_managed_data_storage_path_rejects_paths_outside_data_root(self):
        with self.assertRaises(ValueError) as cm:
            managed_paths.to_managed_data_storage_path(
                "uploads/demo.txt",
                field_name="paper_download_items.file_path",
            )

        self.assertIn("path_must_start_with_data", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
