import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from backend.app.core.config import settings
from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.services.knowledge_ingestion import KnowledgeIngestionError, KnowledgeIngestionManager


class _UploadFile:
    def __init__(self, filename: str, content: bytes, content_type: str | None = None):
        self.filename = filename
        self._content = content
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._content


class _KbStore:
    def create_document(self, **kwargs):
        return SimpleNamespace(
            doc_id="d1",
            filename=kwargs["filename"],
            file_path=kwargs["file_path"],
            file_size=kwargs["file_size"],
            mime_type=kwargs["mime_type"],
            uploaded_by=kwargs["uploaded_by"],
            status=kwargs["status"],
            kb_id=kwargs["kb_id"],
            kb_dataset_id=kwargs["kb_dataset_id"],
            kb_name=kwargs["kb_name"],
        )


class _RagflowService:
    def normalize_dataset_id(self, kb_ref: str):  # noqa: ARG002
        return None

    def resolve_dataset_name(self, kb_ref: str):  # noqa: ARG002
        return None


@dataclass
class _Ctx:
    payload: object
    snapshot: PermissionSnapshot


class _UploadSettingsStore:
    def __init__(self, values):
        self._values = list(values)

    def get(self):
        return SimpleNamespace(allowed_extensions=list(self._values), updated_at_ms=0)

    def add_allowed_extension_if_missing(self, extension: str):
        ext = str(extension or "").strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        if ext not in self._values:
            self._values.append(ext)
        self._values = sorted(set(self._values))
        return self.get()


class TestKnowledgeIngestionManagerUnit(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._upload_dir_old = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = self._tmp.name
        self.deps = SimpleNamespace(
            kb_store=_KbStore(),
            ragflow_service=_RagflowService(),
            audit_log_store=None,
            user_store=None,
            org_directory_store=None,
            upload_settings_store=None,
        )
        self.ctx = _Ctx(
            payload=SimpleNamespace(sub="u1"),
            snapshot=PermissionSnapshot(
                is_admin=True,
                can_upload=True,
                can_review=True,
                can_download=True,
                can_delete=True,
                kb_scope=ResourceScope.ALL,
                kb_names=frozenset(),
                chat_scope=ResourceScope.NONE,
                chat_ids=frozenset(),
            ),
        )
        self.manager = KnowledgeIngestionManager(self.deps)

    async def asyncTearDown(self):
        settings.UPLOAD_DIR = self._upload_dir_old
        self._tmp.cleanup()

    async def test_stage_upload_success_with_image_mime(self):
        upload = _UploadFile(filename="x.png", content=b"abc", content_type=None)
        doc = await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
        self.assertEqual(doc.mime_type, "image/png")
        self.assertEqual(doc.status, "pending")

    async def test_stage_upload_rejects_unsupported_extension(self):
        upload = _UploadFile(filename="x.exe", content=b"abc", content_type=None)
        with self.assertRaises(KnowledgeIngestionError) as cm:
            await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
        self.assertEqual(cm.exception.code, "unsupported_file_type")

    async def test_stage_upload_supports_nested_relative_path(self):
        upload = _UploadFile(filename="folder/sub/123.txt", content=b"abc", content_type=None)
        doc = await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
        self.assertEqual(doc.filename, "folder/sub/123.txt")
        self.assertTrue(Path(doc.file_path).exists())
        self.assertEqual(Path(doc.file_path).read_bytes(), b"abc")
        self.assertTrue(str(doc.file_path).endswith(str(Path("folder") / "sub" / "123.txt")))

    async def test_stage_upload_rejects_parent_traversal_path(self):
        upload = _UploadFile(filename="../evil.txt", content=b"abc", content_type=None)
        with self.assertRaises(KnowledgeIngestionError) as cm:
            await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
        self.assertEqual(cm.exception.code, "invalid_filename")

    async def test_stage_upload_auto_adds_missing_extension_without_admin_step(self):
        old_allowed = set(settings.ALLOWED_EXTENSIONS)
        try:
            # Simulate a suffix unknown to backend static baseline and DB list.
            settings.ALLOWED_EXTENSIONS = {x for x in old_allowed if x != ".xyz"}
            self.deps.upload_settings_store = _UploadSettingsStore(
                [x for x in old_allowed if x != ".xyz"]
            )
            upload = _UploadFile(filename="sample.xyz", content=b"abc", content_type=None)
            doc = await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
            self.assertEqual(doc.filename, "sample.xyz")
            self.assertIn(".xyz", self.deps.upload_settings_store.get().allowed_extensions)
        finally:
            settings.ALLOWED_EXTENSIONS = old_allowed


if __name__ == "__main__":
    unittest.main()
