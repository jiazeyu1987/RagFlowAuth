from __future__ import annotations

import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.services.audit_helpers import actor_fields_from_ctx


class KnowledgeIngestionKbPort(Protocol):
    def create_document(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        uploaded_by: str,
        kb_id: str,
        kb_dataset_id: str | None,
        kb_name: str | None,
        status: str = "pending",
    ): ...


@dataclass
class KnowledgeIngestionError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class KnowledgeIngestionManager:
    """
    Reusable knowledge-upload ingestion manager.
    """

    def __init__(self, deps: object):
        self._deps = deps

    @staticmethod
    def _detect_mime(upload_filename: str, content_type: str | None) -> str:
        file_ext = Path(upload_filename).suffix.lower()
        guessed_mime, _ = mimetypes.guess_type(upload_filename)
        mime_type = (content_type or guessed_mime or "application/octet-stream").strip()
        if file_ext in {".txt", ".ini", ".log"}:
            return "text/plain; charset=utf-8"
        if file_ext in {".md", ".markdown"}:
            return "text/markdown; charset=utf-8"
        if file_ext in {".csv"}:
            return "text/csv; charset=utf-8"
        if file_ext in {".xlsx"}:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if file_ext in {".xls"}:
            return "application/vnd.ms-excel"
        if file_ext in {".png"}:
            return "image/png"
        if file_ext in {".jpg", ".jpeg"}:
            return "image/jpeg"
        return mime_type

    @staticmethod
    def _normalize_relative_upload_path(upload_filename: str) -> tuple[str, Path]:
        raw = str(upload_filename or "").replace("\\", "/").strip()
        if not raw:
            raise KnowledgeIngestionError("invalid_filename", status_code=400)

        pure = PurePosixPath(raw)
        parts = []
        for part in pure.parts:
            token = str(part or "").strip()
            if not token or token == ".":
                continue
            if token == "..":
                raise KnowledgeIngestionError("invalid_filename", status_code=400)
            if ":" in token:
                raise KnowledgeIngestionError("invalid_filename", status_code=400)
            parts.append(token)

        if not parts:
            raise KnowledgeIngestionError("invalid_filename", status_code=400)

        return "/".join(parts), Path(*parts)

    async def stage_upload_knowledge(self, *, kb_ref: str, upload_file, ctx):
        from backend.app.core.permission_resolver import assert_can_upload, assert_kb_allowed

        deps = self._deps
        snapshot = ctx.snapshot
        kb_info = resolve_kb_ref(deps, kb_ref)
        assert_can_upload(snapshot)
        assert_kb_allowed(snapshot, kb_ref)

        content = await upload_file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise KnowledgeIngestionError("file_too_large", status_code=400)

        display_name, relative_path = self._normalize_relative_upload_path(upload_file.filename)
        file_ext = Path(display_name).suffix.lower()
        upload_settings_store = getattr(deps, "upload_settings_store", None)
        allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
        if upload_settings_store is not None:
            try:
                allowed_extensions = set(upload_settings_store.get().allowed_extensions)
            except Exception:
                allowed_extensions = set(settings.ALLOWED_EXTENSIONS)

        if file_ext not in allowed_extensions:
            raise KnowledgeIngestionError("unsupported_file_type", status_code=400)

        uploads_dir = resolve_repo_path(settings.UPLOAD_DIR)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        staged_root = uploads_dir / str(uuid.uuid4())
        file_path = staged_root / relative_path
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
        except Exception as e:
            raise KnowledgeIngestionError(f"write_file_failed:{e}", status_code=500) from e

        mime_type = self._detect_mime(display_name, getattr(upload_file, "content_type", None))

        doc = deps.kb_store.create_document(
            filename=display_name,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=mime_type,
            uploaded_by=ctx.payload.sub,
            kb_id=(kb_info.dataset_id or kb_ref),
            kb_dataset_id=kb_info.dataset_id,
            kb_name=(kb_info.name or kb_ref),
            status="pending",
        )

        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_upload",
                    actor=ctx.payload.sub,
                    source="knowledge",
                    doc_id=doc.doc_id,
                    filename=doc.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta={"file_size": getattr(doc, "file_size", None), "status": getattr(doc, "status", None)},
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass
        return doc
