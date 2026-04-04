from __future__ import annotations

import logging
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.services.audit_helpers import actor_fields_from_ctx

logger = logging.getLogger(__name__)


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

    def finalize_document(self, *, doc, reviewed_by: str, review_notes: str | None = None):
        file_path = Path(str(getattr(doc, "file_path", "") or ""))
        if not file_path.exists():
            raise KnowledgeIngestionError("local_file_missing", status_code=409)

        try:
            file_content = file_path.read_bytes()
        except Exception as e:
            raise KnowledgeIngestionError(f"read_file_failed:{e}", status_code=500) from e

        try:
            ragflow_doc_id = self._deps.ragflow_service.upload_document_blob(
                file_filename=str(getattr(doc, "filename", "") or file_path.name),
                file_content=file_content,
                kb_id=str(getattr(doc, "kb_id", "") or ""),
            )
        except Exception as e:
            raise KnowledgeIngestionError(f"ragflow_upload_failed:{e}", status_code=500) from e

        if not ragflow_doc_id:
            raise KnowledgeIngestionError("ragflow_upload_failed", status_code=500)

        dataset_ref = (
            str(getattr(doc, "kb_dataset_id", "") or "").strip()
            or str(getattr(doc, "kb_id", "") or "").strip()
            or str(getattr(doc, "kb_name", "") or "").strip()
        )
        if ragflow_doc_id != "uploaded":
            try:
                ok = self._deps.ragflow_service.parse_document(
                    dataset_ref=dataset_ref,
                    document_id=str(ragflow_doc_id),
                )
                if not ok:
                    logger.warning(
                        "Parse trigger failed after auto-approving uploaded document: doc_id=%s ragflow_doc_id=%s dataset_ref=%s",
                        getattr(doc, "doc_id", None),
                        ragflow_doc_id,
                        dataset_ref,
                    )
            except Exception:
                logger.warning(
                    "Parse trigger raised after auto-approving uploaded document: doc_id=%s ragflow_doc_id=%s dataset_ref=%s",
                    getattr(doc, "doc_id", None),
                    ragflow_doc_id,
                    dataset_ref,
                    exc_info=True,
                )

        updated = self._deps.kb_store.update_document_status(
            doc_id=str(getattr(doc, "doc_id", "") or ""),
            status="approved",
            reviewed_by=str(reviewed_by or getattr(doc, "uploaded_by", "") or ""),
            review_notes=str(review_notes or "").strip() or None,
            ragflow_doc_id=str(ragflow_doc_id),
        )
        if updated is None:
            raise KnowledgeIngestionError("document_status_update_failed", status_code=500)
        return updated

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

        display_name, relative_path = self._normalize_relative_upload_path(upload_file.filename)
        file_ext = Path(display_name).suffix.lower()
        upload_settings_store = getattr(deps, "upload_settings_store", None)
        allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
        if upload_settings_store is not None:
            try:
                allowed_extensions = set(upload_settings_store.get().allowed_extensions)
            except Exception as e:
                raise KnowledgeIngestionError(f"upload_settings_unavailable:{e}", status_code=500) from e

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

        doc = self.finalize_document(
            doc=doc,
            reviewed_by=str(ctx.payload.sub),
            review_notes="direct_upload_ingestion_completed",
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
