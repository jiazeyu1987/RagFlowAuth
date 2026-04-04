from __future__ import annotations

import io
import json
import mimetypes
import os
import urllib.parse
import logging
import time
from dataclasses import dataclass
from pathlib import Path
import zipfile

from fastapi import HTTPException
from fastapi.responses import Response

from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    assert_can_delete,
    assert_can_download,
    assert_can_review,
    assert_kb_allowed,
)
from backend.services.documents.errors import DocumentNotFound, DocumentSourceError
from backend.services.documents.models import DeleteResult, DocumentRef
from backend.services.documents.sources.knowledge_source import KnowledgeDocumentSource
from backend.services.documents.sources.ragflow_source import RagflowDocumentSource
from backend.services.watermarking import DocumentWatermarkService
from backend.services.audit_helpers import actor_fields_from_ctx, actor_fields_from_user
from backend.app.core.request_id import get_request_id

logger = logging.getLogger(__name__)

VISIBLE_TEXT_WATERMARK_EXTENSIONS = {".txt", ".md", ".csv", ".log"}


@dataclass(frozen=True)
class DownloadArtifact:
    content: bytes
    filename: str
    media_type: str
    distribution_mode: str
    watermark: dict


@dataclass
class DocumentManager:
    deps: object

    def __post_init__(self) -> None:
        self._ragflow = RagflowDocumentSource(self.deps)
        self._knowledge = KnowledgeDocumentSource(self.deps)

    def _content_disposition(self, filename: str) -> str:
        try:
            filename.encode("ascii")
            return f'attachment; filename="{filename}"'
        except UnicodeEncodeError:
            ascii_filename = filename.encode("ascii", "replace").decode("ascii")
            encoded_filename = urllib.parse.quote(filename)
            return f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"

    def _watermark_service(self) -> DocumentWatermarkService:
        return DocumentWatermarkService(
            store=getattr(self.deps, "watermark_policy_store", None),
            org_structure_manager=getattr(self.deps, "org_structure_manager", None),
        )

    @staticmethod
    def _decode_text_content(content: bytes) -> tuple[str, str]:
        for encoding in ("utf-8", "gbk"):
            try:
                return encoding, content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise RuntimeError("watermark_text_decode_failed")

    @staticmethod
    def _text_watermark_block(watermark_text: str) -> str:
        return "\n".join(
            [
                "[受控分发水印]",
                watermark_text,
                "[/受控分发水印]",
                "",
            ]
        )

    def _apply_text_watermark(self, *, content: bytes, watermark_text: str) -> bytes:
        encoding, decoded = self._decode_text_content(content)
        combined = f"{self._text_watermark_block(watermark_text)}\n{decoded}"
        return combined.encode(encoding)

    @staticmethod
    def _package_filename(filename: str) -> str:
        path = Path(filename or "document")
        stem = path.stem or "document"
        return f"{stem}__controlled_distribution.zip"

    def _build_controlled_package(
        self,
        *,
        filename: str,
        content: bytes,
        source: str,
        watermark: dict,
    ) -> bytes:
        service = self._watermark_service()
        note_text = service.build_distribution_note(
            watermark=watermark,
            filename=filename,
            source=source,
            item_count=1,
        )
        manifest = service.build_manifest(
            watermark=watermark,
            source=source,
            filename=filename,
            distribution_mode="controlled_package",
            documents=[{"doc_id": watermark.get("doc_id"), "filename": filename}],
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("00_CONTROLLED_DISTRIBUTION.txt", note_text.encode("utf-8"))
            zip_file.writestr(
                "watermark_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            zip_file.writestr(filename, content)
        return buffer.getvalue()

    def _rewrite_zip_with_watermark(
        self,
        *,
        zip_content: bytes,
        filename: str,
        source: str,
        watermark: dict,
        documents: list[dict],
    ) -> bytes:
        service = self._watermark_service()
        note_text = service.build_distribution_note(
            watermark=watermark,
            filename=filename,
            source=source,
            item_count=len(documents),
        )
        manifest = service.build_manifest(
            watermark=watermark,
            source=source,
            filename=filename,
            distribution_mode="batch_zip",
            documents=documents,
        )
        src = io.BytesIO(zip_content)
        dst = io.BytesIO()
        try:
            with zipfile.ZipFile(src, "r") as input_zip, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as output_zip:
                output_zip.writestr("00_CONTROLLED_DISTRIBUTION.txt", note_text.encode("utf-8"))
                output_zip.writestr(
                    "watermark_manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
                )
                for info in input_zip.infolist():
                    output_zip.writestr(info.filename, input_zip.read(info.filename))
        except zipfile.BadZipFile as exc:
            raise RuntimeError("watermark_batch_zip_invalid") from exc
        return dst.getvalue()

    def _build_download_artifact(
        self,
        *,
        content: bytes,
        filename: str,
        source: str,
        doc_id: str,
        ctx,
        media_type: str | None = None,
    ) -> DownloadArtifact:
        service = self._watermark_service()
        watermark = service.build_watermark(
            user=getattr(ctx, "user", None),
            payload_sub=getattr(getattr(ctx, "payload", None), "sub", None),
            purpose="download",
            doc_id=doc_id,
            filename=filename,
            source=source,
        )
        ext = Path(filename or "").suffix.lower()
        if ext in VISIBLE_TEXT_WATERMARK_EXTENSIONS:
            return DownloadArtifact(
                content=self._apply_text_watermark(content=content, watermark_text=str(watermark.get("text") or "")),
                filename=filename,
                media_type=(media_type or mimetypes.guess_type(filename)[0] or "text/plain; charset=utf-8"),
                distribution_mode="inline_text_watermark",
                watermark=watermark,
            )

        return DownloadArtifact(
            content=self._build_controlled_package(
                filename=filename,
                content=content,
                source=source,
                watermark=watermark,
            ),
            filename=self._package_filename(filename),
            media_type="application/zip",
            distribution_mode="controlled_package",
            watermark=watermark,
        )

    def _download_response_from_artifact(self, artifact: DownloadArtifact) -> Response:
        return Response(
            content=artifact.content,
            media_type=artifact.media_type,
            headers={
                "Content-Disposition": self._content_disposition(artifact.filename),
                "X-Watermark-Policy-Id": str(artifact.watermark.get("policy_id") or ""),
                "X-Distribution-Mode": artifact.distribution_mode,
            },
        )

    @staticmethod
    def _is_retired_document(doc) -> bool:
        return str(getattr(doc, "effective_status", "") or "").strip().lower() == "archived"

    # -------------------- Preview (JSON contract) --------------------

    def preview_payload(
        self,
        ref: DocumentRef,
        *,
        preview_filename: str | None = None,
        render: str = "default",
        ctx=None,
    ):
        """
        Return a unified preview JSON payload.
        This is used by the unified preview gateway and can be reused by other modules.
        """
        t0 = time.perf_counter()
        request_id = get_request_id() or "-"
        fetch_t0 = time.perf_counter()
        if ref.source == "ragflow":
            doc_bytes = self._ragflow.get_bytes(ref)
        else:
            doc_bytes = self._knowledge.get_bytes(ref)
        source_fetch_ms = (time.perf_counter() - fetch_t0) * 1000

        from backend.services.unified_preview import build_preview_payload

        transform_t0 = time.perf_counter()
        payload = build_preview_payload(
            doc_bytes.content,
            preview_filename or doc_bytes.filename,
            doc_id=ref.doc_id,
            render=render,
        )
        if ctx is not None:
            payload["watermark"] = self._watermark_service().build_watermark(
                user=getattr(ctx, "user", None),
                payload_sub=getattr(getattr(ctx, "payload", None), "sub", None),
                purpose="preview",
                doc_id=ref.doc_id,
                filename=str(payload.get("source_filename") or payload.get("filename") or doc_bytes.filename or ""),
                source=ref.source,
            )
        transform_ms = (time.perf_counter() - transform_t0) * 1000
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "preview_payload_done request_id=%s source=%s doc_id=%s dataset=%s filename=%s size_bytes=%s render=%s type=%s source_fetch_ms=%.2f transform_ms=%.2f elapsed_ms=%.2f",
            request_id,
            ref.source,
            ref.doc_id,
            getattr(ref, "dataset_name", None),
            preview_filename or doc_bytes.filename,
            len(doc_bytes.content or b""),
            render,
            payload.get("type"),
            source_fetch_ms,
            transform_ms,
            elapsed_ms,
        )
        return payload

    # -------------------- Download --------------------

    def download_ragflow_response(self, *, doc_id: str, dataset: str, filename: str | None, ctx):
        snapshot = ctx.snapshot
        assert_can_download(snapshot)
        assert_kb_allowed(snapshot, resolve_kb_ref(self.deps, dataset).variants)

        try:
            doc_bytes = self._ragflow.get_bytes(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset))
        except DocumentNotFound as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DocumentSourceError as e:
            raise HTTPException(status_code=500, detail=f"下载文档失败: {str(e)}")

        final_filename = filename or doc_bytes.filename or f"document_{doc_id}"
        artifact = self._build_download_artifact(
            content=doc_bytes.content,
            filename=final_filename,
            source="ragflow",
            doc_id=doc_id,
            ctx=ctx,
            media_type=mimetypes.guess_type(final_filename)[0] or "application/octet-stream",
        )

        kb_id = dataset
        self.deps.download_log_store.log_download(
            doc_id=doc_id,
            filename=artifact.filename,
            kb_id=kb_id,
            downloaded_by=ctx.payload.sub,
            ragflow_doc_id=doc_id,
            is_batch=False,
            kb_dataset_id=None,
            kb_name=kb_id,
        )
        audit = getattr(self.deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_download",
                    actor=ctx.payload.sub,
                    source="ragflow",
                    doc_id=doc_id,
                    filename=artifact.filename,
                    kb_id=kb_id,
                    kb_name=kb_id,
                    meta={
                        "is_batch": False,
                        "distribution_mode": artifact.distribution_mode,
                        "watermark_policy_id": artifact.watermark.get("policy_id"),
                        "original_filename": final_filename,
                    },
                    **actor_fields_from_ctx(self.deps, ctx),
                )
            except Exception:
                pass

        return self._download_response_from_artifact(artifact)

    def download_knowledge_response(self, *, doc_id: str, ctx):
        deps = self.deps
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")
        if self._is_retired_document(doc):
            raise HTTPException(status_code=409, detail="document_retired_use_archive_route")

        assert_kb_allowed(snapshot, doc.kb_id)
        if not os.path.exists(doc.file_path):
            raise HTTPException(status_code=404, detail="file_not_found")

        with open(doc.file_path, "rb") as file_obj:
            original_content = file_obj.read()

        artifact = self._build_download_artifact(
            content=original_content,
            filename=doc.filename,
            source="knowledge",
            doc_id=doc.doc_id,
            ctx=ctx,
            media_type=doc.mime_type,
        )

        deps.download_log_store.log_download(
            doc_id=doc.doc_id,
            filename=artifact.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            downloaded_by=ctx.payload.sub,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
        )
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_download",
                    actor=ctx.payload.sub,
                    source="knowledge",
                    doc_id=doc.doc_id,
                    filename=artifact.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta={
                        "is_batch": False,
                        "distribution_mode": artifact.distribution_mode,
                        "watermark_policy_id": artifact.watermark.get("policy_id"),
                        "original_filename": doc.filename,
                    },
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass
        return self._download_response_from_artifact(artifact)

    def download_retired_knowledge_response(self, *, doc_id: str, ctx):
        deps = self.deps
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        from backend.services.compliance import RetiredRecordsService

        service = RetiredRecordsService(kb_store=deps.kb_store)
        try:
            doc = service.get_retired_document(doc_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            detail = str(exc)
            if detail == "document_retention_expired":
                raise HTTPException(status_code=410, detail=detail) from exc
            raise HTTPException(status_code=409, detail=detail) from exc

        assert_kb_allowed(snapshot, doc.kb_id)
        if not os.path.exists(doc.file_path):
            raise HTTPException(status_code=404, detail="file_not_found")

        with open(doc.file_path, "rb") as file_obj:
            original_content = file_obj.read()

        artifact = self._build_download_artifact(
            content=original_content,
            filename=doc.filename,
            source="knowledge_retired",
            doc_id=doc.doc_id,
            ctx=ctx,
            media_type=doc.mime_type,
        )

        deps.download_log_store.log_download(
            doc_id=doc.doc_id,
            filename=artifact.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            downloaded_by=ctx.payload.sub,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
        )
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="retired_document_download",
                    actor=ctx.payload.sub,
                    source="knowledge_retired",
                    doc_id=doc.doc_id,
                    filename=artifact.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta={
                        "distribution_mode": artifact.distribution_mode,
                        "watermark_policy_id": artifact.watermark.get("policy_id"),
                        "original_filename": doc.filename,
                        "archived_at_ms": getattr(doc, "archived_at_ms", None),
                        "retention_until_ms": getattr(doc, "retention_until_ms", None),
                    },
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass
        return self._download_response_from_artifact(artifact)

    def batch_download_knowledge_response(self, *, doc_ids: list[str], ctx):
        deps = self.deps
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        valid_docs = []
        for doc_id in doc_ids:
            doc = deps.kb_store.get_document(doc_id)
            if not doc:
                continue
            if self._is_retired_document(doc):
                continue
            assert_kb_allowed(snapshot, doc.kb_id)
            if not os.path.exists(doc.file_path):
                continue
            valid_docs.append(doc)

        if not valid_docs:
            raise HTTPException(status_code=404, detail="没有找到可下载的文档")

        service = self._watermark_service()
        watermark = service.build_watermark(
            user=getattr(ctx, "user", None),
            payload_sub=getattr(getattr(ctx, "payload", None), "sub", None),
            purpose="batch_download",
            doc_id=f"knowledge-batch-{len(valid_docs)}",
            filename=f"knowledge_batch_{len(valid_docs)}",
            source="knowledge",
        )

        zip_buffer = io.BytesIO()
        created_at_ms = int(time.time() * 1000)
        used_names: set[str] = set()
        documents: list[dict] = []
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                "00_CONTROLLED_DISTRIBUTION.txt",
                service.build_distribution_note(
                    watermark=watermark,
                    filename=f"knowledge_batch_{len(valid_docs)}",
                    source="knowledge",
                    item_count=len(valid_docs),
                ).encode("utf-8"),
            )
            for doc in valid_docs:
                zip_name = doc.filename
                counter = 1
                base, ext = os.path.splitext(zip_name)
                while zip_name in used_names:
                    zip_name = f"{base}_{counter}{ext}"
                    counter += 1
                used_names.add(zip_name)
                zip_file.write(doc.file_path, zip_name)
                documents.append(
                    {
                        "doc_id": doc.doc_id,
                        "filename": doc.filename,
                        "distributed_filename": zip_name,
                        "kb_id": doc.kb_id,
                    }
                )
            zip_file.writestr(
                "watermark_manifest.json",
                json.dumps(
                    service.build_manifest(
                        watermark=watermark,
                        source="knowledge",
                        filename=f"documents_{created_at_ms}.zip",
                        documents=documents,
                        distribution_mode="batch_zip",
                    ),
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )

        zip_buffer.seek(0)
        zip_filename = f"documents_{created_at_ms}.zip"
        for doc in valid_docs:
            deps.download_log_store.log_download(
                doc_id=doc.doc_id,
                filename=zip_filename,
                kb_id=(doc.kb_name or doc.kb_id),
                downloaded_by=ctx.payload.sub,
                is_batch=True,
                kb_dataset_id=doc.kb_dataset_id,
                kb_name=doc.kb_name,
            )

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": self._content_disposition(zip_filename),
                "X-Watermark-Policy-Id": str(watermark.get("policy_id") or ""),
                "X-Distribution-Mode": "batch_zip",
            },
        )

    def batch_download_ragflow_response(self, *, documents_info: list[dict], ctx):
        deps = self.deps
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        if not documents_info:
            raise HTTPException(status_code=400, detail="no_documents_selected")

        documents: list[dict] = []
        for doc_info in documents_info:
            dataset = doc_info.get("dataset", "展厅")
            assert_kb_allowed(snapshot, dataset)
            documents.append(
                {
                    "doc_id": doc_info.get("doc_id") or doc_info.get("id"),
                    "filename": doc_info.get("name", "unknown"),
                    "dataset": dataset,
                }
            )

        zip_content, filename = deps.ragflow_service.batch_download_documents(documents_info)
        if zip_content is None:
            raise HTTPException(status_code=500, detail="批量下载失败")

        service = self._watermark_service()
        watermark = service.build_watermark(
            user=getattr(ctx, "user", None),
            payload_sub=getattr(getattr(ctx, "payload", None), "sub", None),
            purpose="batch_download",
            doc_id=f"ragflow-batch-{len(documents)}",
            filename=filename or f"ragflow_batch_{len(documents)}.zip",
            source="ragflow",
        )
        watermarked_zip = self._rewrite_zip_with_watermark(
            zip_content=zip_content,
            filename=filename or f"ragflow_batch_{len(documents)}.zip",
            source="ragflow",
            watermark=watermark,
            documents=documents,
        )

        for doc_info in documents_info:
            doc_id = doc_info.get("doc_id") or doc_info.get("id")
            doc_name = doc_info.get("name", "unknown")
            dataset = doc_info.get("dataset", "展厅")
            kb_info = resolve_kb_ref(deps, dataset)
            deps.download_log_store.log_download(
                doc_id=doc_id,
                filename=filename or "documents.zip",
                kb_id=(kb_info.dataset_id or dataset),
                downloaded_by=ctx.payload.sub,
                ragflow_doc_id=doc_id,
                is_batch=True,
                kb_dataset_id=kb_info.dataset_id,
                kb_name=(kb_info.name or dataset),
            )

        return Response(
            content=watermarked_zip,
            media_type="application/zip",
            headers={
                "Content-Disposition": self._content_disposition(filename or "documents.zip"),
                "X-Watermark-Policy-Id": str(watermark.get("policy_id") or ""),
                "X-Distribution-Mode": "batch_zip",
            },
        )

    # -------------------- Upload (knowledge local staging) --------------------

    async def stage_upload_knowledge(self, *, kb_ref: str, upload_file, ctx):
        from backend.services.knowledge_ingestion import KnowledgeIngestionError, KnowledgeIngestionManager

        ingestion_manager = getattr(self.deps, "knowledge_ingestion_manager", None)
        if ingestion_manager is None:
            ingestion_manager = KnowledgeIngestionManager(deps=self.deps)
        try:
            return await ingestion_manager.stage_upload_knowledge(kb_ref=kb_ref, upload_file=upload_file, ctx=ctx)
        except KnowledgeIngestionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.code) from e
    # -------------------- Delete --------------------

    def delete_knowledge_document(self, *, doc_id: str, ctx) -> DeleteResult:
        deps = self.deps
        snapshot = ctx.snapshot
        assert_can_delete(snapshot)

        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")
        assert_kb_allowed(snapshot, doc.kb_id)

        ragflow_ok = None
        ragflow_err = None
        if doc.ragflow_doc_id:
            dataset_ref = doc.kb_dataset_id or doc.kb_id or (doc.kb_name or "")
            try:
                ragflow_ok = 1 if deps.ragflow_service.delete_document(doc.ragflow_doc_id, dataset_name=dataset_ref) else 0
            except Exception as e:
                ragflow_ok = 0
                ragflow_err = str(e)
            if ragflow_ok == 0 and not ragflow_err:
                ragflow_err = "ragflow_delete_failed"

        deps.deletion_log_store.log_deletion(
            doc_id=doc.doc_id,
            filename=doc.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            deleted_by=ctx.payload.sub,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
            original_uploader=doc.uploaded_by,
            original_reviewer=doc.reviewed_by,
            ragflow_doc_id=doc.ragflow_doc_id,
            action="delete",
            ragflow_deleted=ragflow_ok,
            ragflow_delete_error=ragflow_err,
        )
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_delete",
                    actor=ctx.payload.sub,
                    source="knowledge",
                    doc_id=doc.doc_id,
                    filename=doc.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta={"ragflow_deleted": bool(ragflow_ok == 1) if ragflow_ok is not None else None},
                    **actor_fields_from_ctx(deps, ctx),
                )
            except Exception:
                pass

        if ragflow_ok == 0:
            raise HTTPException(status_code=500, detail=f"ragflow_delete_failed:{ragflow_err}")

        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        deps.kb_store.delete_document(doc_id)

        return DeleteResult(ok=True, message="document_deleted", ragflow_deleted=(ragflow_ok == 1 if ragflow_ok is not None else None))

    def delete_knowledge_document_trusted(
        self,
        *,
        doc_id: str,
        actor_user_id: str,
        actor_user=None,
        approval_request_id: str | None = None,
    ) -> DeleteResult:
        deps = self.deps
        doc = deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")

        ragflow_ok = None
        ragflow_err = None
        if doc.ragflow_doc_id:
            dataset_ref = doc.kb_dataset_id or doc.kb_id or (doc.kb_name or "")
            try:
                ragflow_ok = 1 if deps.ragflow_service.delete_document(doc.ragflow_doc_id, dataset_name=dataset_ref) else 0
            except Exception as e:
                ragflow_ok = 0
                ragflow_err = str(e)
            if ragflow_ok == 0 and not ragflow_err:
                ragflow_err = "ragflow_delete_failed"

        deps.deletion_log_store.log_deletion(
            doc_id=doc.doc_id,
            filename=doc.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            deleted_by=actor_user_id,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
            original_uploader=doc.uploaded_by,
            original_reviewer=doc.reviewed_by,
            ragflow_doc_id=doc.ragflow_doc_id,
            action="delete",
            ragflow_deleted=ragflow_ok,
            ragflow_delete_error=ragflow_err,
        )
        audit = getattr(deps, "audit_log_store", None)
        if audit:
            try:
                meta = {"ragflow_deleted": bool(ragflow_ok == 1 if ragflow_ok is not None else False)}
                if approval_request_id:
                    meta["approval_request_id"] = approval_request_id
                audit_kwargs = {}
                if actor_user is not None:
                    audit_kwargs = actor_fields_from_user(deps, actor_user)
                audit.log_event(
                    action="document_delete",
                    actor=actor_user_id,
                    source="knowledge",
                    doc_id=doc.doc_id,
                    filename=doc.filename,
                    kb_id=(doc.kb_name or doc.kb_id),
                    kb_dataset_id=getattr(doc, "kb_dataset_id", None),
                    kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
                    meta=meta,
                    **audit_kwargs,
                )
            except Exception:
                pass

        if ragflow_ok == 0:
            raise HTTPException(status_code=500, detail=f"ragflow_delete_failed:{ragflow_err}")

        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        deps.kb_store.delete_document(doc_id)

        return DeleteResult(ok=True, message="document_deleted", ragflow_deleted=(ragflow_ok == 1 if ragflow_ok is not None else None))

    def delete_ragflow_document(self, *, doc_id: str, dataset_name: str, ctx) -> DeleteResult:
        snapshot = ctx.snapshot
        assert_can_delete(snapshot)
        assert_kb_allowed(snapshot, resolve_kb_ref(self.deps, dataset_name).variants)

        kb_info = None
        local_doc = None
        try:
            kb_info = resolve_kb_ref(self.deps, dataset_name)
            local_doc = self.deps.kb_store.get_document_by_ragflow_id(doc_id, dataset_name, kb_refs=list(kb_info.variants))
        except Exception:
            kb_info = None
            local_doc = None

        success = self._ragflow.delete(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset_name))
        if not success:
            raise HTTPException(status_code=404, detail="document_not_found_or_delete_failed")

        audit = getattr(self.deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="document_delete",
                    actor=ctx.payload.sub,
                    source="ragflow",
                    doc_id=doc_id,
                    filename=(local_doc.filename if local_doc else None),
                    kb_id=(getattr(local_doc, "kb_name", None) or getattr(local_doc, "kb_id", None) or dataset_name),
                    kb_dataset_id=getattr(local_doc, "kb_dataset_id", None) if local_doc else None,
                    kb_name=getattr(local_doc, "kb_name", None) if local_doc else dataset_name,
                    meta={"ragflow_deleted": True},
                    **actor_fields_from_ctx(self.deps, ctx),
                )
            except Exception:
                pass

        if local_doc:
            self.deps.deletion_log_store.log_deletion(
                doc_id=local_doc.doc_id,
                filename=local_doc.filename,
                kb_id=local_doc.kb_id,
                deleted_by=ctx.payload.sub,
                kb_dataset_id=getattr(local_doc, "kb_dataset_id", None),
                kb_name=getattr(local_doc, "kb_name", None),
                original_uploader=local_doc.uploaded_by,
                original_reviewer=local_doc.reviewed_by,
                ragflow_doc_id=doc_id,
            )
            if os.path.exists(local_doc.file_path):
                os.remove(local_doc.file_path)
            self.deps.kb_store.delete_document(local_doc.doc_id)

        return DeleteResult(ok=True, message="document_deleted", ragflow_deleted=True)

    # -------------------- Review preview policy --------------------

    def assert_can_preview_knowledge(self, snapshot):
        try:
            assert_can_download(snapshot)
        except Exception:
            assert_can_review(snapshot)
