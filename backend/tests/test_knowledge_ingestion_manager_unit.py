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
    def __init__(self):
        self.created_documents = []

    def create_document(self, **kwargs):
        doc = SimpleNamespace(
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
        self.created_documents.append(doc)
        return doc

    def update_document_status(self, *, doc_id: str, status: str, reviewed_by: str | None = None, review_notes: str | None = None, ragflow_doc_id: str | None = None):  # noqa: ARG002
        if not self.created_documents:
            return None
        doc = self.created_documents[-1]
        doc.status = status
        doc.reviewed_by = reviewed_by
        doc.review_notes = review_notes
        doc.ragflow_doc_id = ragflow_doc_id
        return doc


class _RagflowService:
    def __init__(self):
        self.uploaded = []
        self.parsed = []

    def normalize_dataset_id(self, kb_ref: str):  # noqa: ARG002
        return None

    def resolve_dataset_name(self, kb_ref: str):  # noqa: ARG002
        return None

    def upload_document_blob(self, file_filename: str, file_content: bytes, kb_id: str = "展厅") -> str:
        self.uploaded.append(
            {
                "file_filename": str(file_filename),
                "file_content": bytes(file_content),
                "kb_id": str(kb_id),
            }
        )
        return "rag-doc-1"

    def parse_document(self, *, dataset_ref: str, document_id: str) -> bool:
        self.parsed.append({"dataset_ref": str(dataset_ref), "document_id": str(document_id)})
        return True


@dataclass
class _Ctx:
    payload: object
    snapshot: PermissionSnapshot


class _UploadSettingsStore:
    def __init__(self, values):
        self._values = list(values)

    def get(self):
        return SimpleNamespace(allowed_extensions=list(self._values), updated_at_ms=0)


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
                can_copy=True,
                can_delete=True,
                can_manage_kb_directory=True,
                can_view_kb_config=True,
                can_view_tools=True,
                kb_scope=ResourceScope.ALL,
                kb_names=frozenset(),
                chat_scope=ResourceScope.NONE,
                chat_ids=frozenset(),
                tool_scope=ResourceScope.ALL,
                tool_ids=frozenset(),
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
        self.assertEqual(doc.status, "approved")

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

    async def test_stage_upload_rejects_missing_extension_without_auto_heal(self):
        old_allowed = set(settings.ALLOWED_EXTENSIONS)
        try:
            settings.ALLOWED_EXTENSIONS = {x for x in old_allowed if x != ".xyz"}
            self.deps.upload_settings_store = _UploadSettingsStore(
                [x for x in old_allowed if x != ".xyz"]
            )
            upload = _UploadFile(filename="sample.xyz", content=b"abc", content_type=None)
            with self.assertRaises(KnowledgeIngestionError) as cm:
                await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
            self.assertEqual(cm.exception.code, "unsupported_file_type")
        finally:
            settings.ALLOWED_EXTENSIONS = old_allowed

    async def test_stage_upload_ignores_max_file_size_setting(self):
        old_max = settings.MAX_FILE_SIZE
        try:
            settings.MAX_FILE_SIZE = 1
            upload = _UploadFile(filename="x.txt", content=b"abc", content_type=None)
            doc = await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
            self.assertEqual(doc.filename, "x.txt")
            self.assertEqual(doc.file_size, 3)
        finally:
            settings.MAX_FILE_SIZE = old_max

    async def test_stage_upload_directly_finalizes_document(self):
        upload = _UploadFile(filename="auto.txt", content=b"abc", content_type=None)
        doc = await self.manager.stage_upload_knowledge(kb_ref="kb1", upload_file=upload, ctx=self.ctx)
        self.assertEqual(doc.status, "approved")
        self.assertEqual(doc.reviewed_by, "u1")
        self.assertEqual(doc.review_notes, "direct_upload_ingestion_completed")
        self.assertEqual(doc.ragflow_doc_id, "rag-doc-1")
        self.assertEqual(self.deps.ragflow_service.uploaded[0]["kb_id"], "kb1")
        self.assertEqual(self.deps.ragflow_service.parsed[0]["dataset_ref"], "kb1")


if __name__ == "__main__":
    unittest.main()
