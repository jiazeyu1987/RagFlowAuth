from __future__ import annotations

import io
import json
import mimetypes
import os
import time
import zipfile

from fastapi import HTTPException

from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import assert_can_download, assert_kb_allowed
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.documents.errors import DocumentNotFound, DocumentSourceError
from backend.services.documents.models import DocumentRef

DEFAULT_RAGFLOW_DATASET = "\u5c55\u5385"
NO_DOWNLOADABLE_DOCUMENTS = "\u6ca1\u6709\u627e\u5230\u53ef\u4e0b\u8f7d\u7684\u6587\u6863"
BATCH_DOWNLOAD_FAILED = "\u6279\u91cf\u4e0b\u8f7d\u5931\u8d25"
DOWNLOAD_FAILED_PREFIX = "\u4e0b\u8f7d\u6587\u6863\u5931\u8d25: "


class DocumentDownloadActions:
    def __init__(
        self,
        *,
        deps,
        knowledge_source,
        ragflow_source,
        watermark_support,
    ):
        self._deps = deps
        self._knowledge = knowledge_source
        self._ragflow = ragflow_source
        self._watermark_support = watermark_support

    @staticmethod
    def _is_retired_document(doc) -> bool:
        return str(getattr(doc, "effective_status", "") or "").strip().lower() == "archived"

    @staticmethod
    def _read_file_bytes(path: str) -> bytes:
        with open(path, "rb") as file_obj:
            return file_obj.read()

    def _log_download_audit(
        self,
        *,
        action: str,
        actor: str,
        source: str,
        doc_id: str,
        filename: str,
        kb_id: str,
        meta: dict,
        ctx,
        kb_dataset_id: str | None = None,
        kb_name: str | None = None,
    ) -> None:
        audit = getattr(self._deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action=action,
                    actor=actor,
                    source=source,
                    doc_id=doc_id,
                    filename=filename,
                    kb_id=kb_id,
                    kb_dataset_id=kb_dataset_id,
                    kb_name=kb_name or kb_id,
                    meta=meta,
                    **actor_fields_from_ctx(self._deps, ctx),
                )
            except Exception:
                pass

    def download_ragflow_response(self, *, doc_id: str, dataset: str, filename: str | None, ctx):
        snapshot = ctx.snapshot
        assert_can_download(snapshot)
        assert_kb_allowed(snapshot, resolve_kb_ref(self._deps, dataset).variants)

        try:
            doc_bytes = self._ragflow.get_bytes(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset))
        except DocumentNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DocumentSourceError as exc:
            raise HTTPException(status_code=500, detail=f"{DOWNLOAD_FAILED_PREFIX}{str(exc)}") from exc

        final_filename = filename or doc_bytes.filename or f"document_{doc_id}"
        artifact = self._watermark_support.build_download_artifact(
            content=doc_bytes.content,
            filename=final_filename,
            source="ragflow",
            doc_id=doc_id,
            ctx=ctx,
            media_type=mimetypes.guess_type(final_filename)[0] or "application/octet-stream",
        )

        kb_id = dataset
        self._deps.download_log_store.log_download(
            doc_id=doc_id,
            filename=artifact.filename,
            kb_id=kb_id,
            downloaded_by=ctx.payload.sub,
            ragflow_doc_id=doc_id,
            is_batch=False,
            kb_dataset_id=None,
            kb_name=kb_id,
        )
        self._log_download_audit(
            action="document_download",
            actor=ctx.payload.sub,
            source="ragflow",
            doc_id=doc_id,
            filename=artifact.filename,
            kb_id=kb_id,
            kb_name=kb_id,
            ctx=ctx,
            meta={
                "is_batch": False,
                "distribution_mode": artifact.distribution_mode,
                "watermark_policy_id": artifact.watermark.get("policy_id"),
                "original_filename": final_filename,
            },
        )
        return self._watermark_support.download_response_from_artifact(artifact)

    def download_knowledge_response(self, *, doc_id: str, ctx):
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        doc = self._deps.kb_store.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="document_not_found")
        if self._is_retired_document(doc):
            raise HTTPException(status_code=409, detail="document_retired_use_archive_route")

        assert_kb_allowed(snapshot, doc.kb_id)
        if not os.path.exists(doc.file_path):
            raise HTTPException(status_code=404, detail="file_not_found")

        artifact = self._watermark_support.build_download_artifact(
            content=self._read_file_bytes(doc.file_path),
            filename=doc.filename,
            source="knowledge",
            doc_id=doc.doc_id,
            ctx=ctx,
            media_type=doc.mime_type,
        )

        self._deps.download_log_store.log_download(
            doc_id=doc.doc_id,
            filename=artifact.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            downloaded_by=ctx.payload.sub,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
        )
        self._log_download_audit(
            action="document_download",
            actor=ctx.payload.sub,
            source="knowledge",
            doc_id=doc.doc_id,
            filename=artifact.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            kb_dataset_id=getattr(doc, "kb_dataset_id", None),
            kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
            ctx=ctx,
            meta={
                "is_batch": False,
                "distribution_mode": artifact.distribution_mode,
                "watermark_policy_id": artifact.watermark.get("policy_id"),
                "original_filename": doc.filename,
            },
        )
        return self._watermark_support.download_response_from_artifact(artifact)

    def download_retired_knowledge_response(self, *, doc_id: str, ctx):
        from backend.services.compliance import RetiredRecordsService

        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        service = RetiredRecordsService(kb_store=self._deps.kb_store)
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

        artifact = self._watermark_support.build_download_artifact(
            content=self._read_file_bytes(doc.file_path),
            filename=doc.filename,
            source="knowledge_retired",
            doc_id=doc.doc_id,
            ctx=ctx,
            media_type=doc.mime_type,
        )

        self._deps.download_log_store.log_download(
            doc_id=doc.doc_id,
            filename=artifact.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            downloaded_by=ctx.payload.sub,
            kb_dataset_id=doc.kb_dataset_id,
            kb_name=doc.kb_name,
        )
        self._log_download_audit(
            action="retired_document_download",
            actor=ctx.payload.sub,
            source="knowledge_retired",
            doc_id=doc.doc_id,
            filename=artifact.filename,
            kb_id=(doc.kb_name or doc.kb_id),
            kb_dataset_id=getattr(doc, "kb_dataset_id", None),
            kb_name=getattr(doc, "kb_name", None) or (doc.kb_name or doc.kb_id),
            ctx=ctx,
            meta={
                "distribution_mode": artifact.distribution_mode,
                "watermark_policy_id": artifact.watermark.get("policy_id"),
                "original_filename": doc.filename,
                "archived_at_ms": getattr(doc, "archived_at_ms", None),
                "retention_until_ms": getattr(doc, "retention_until_ms", None),
            },
        )
        return self._watermark_support.download_response_from_artifact(artifact)

    def batch_download_knowledge_response(self, *, doc_ids: list[str], ctx):
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        valid_docs = []
        for doc_id in doc_ids:
            doc = self._deps.kb_store.get_document(doc_id)
            if not doc:
                continue
            if self._is_retired_document(doc):
                continue
            assert_kb_allowed(snapshot, doc.kb_id)
            if not os.path.exists(doc.file_path):
                continue
            valid_docs.append(doc)

        if not valid_docs:
            raise HTTPException(status_code=404, detail=NO_DOWNLOADABLE_DOCUMENTS)

        service = self._watermark_support.watermark_service()
        watermark = self._watermark_support.build_watermark(
            ctx=ctx,
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

        zip_filename = f"documents_{created_at_ms}.zip"
        for doc in valid_docs:
            self._deps.download_log_store.log_download(
                doc_id=doc.doc_id,
                filename=zip_filename,
                kb_id=(doc.kb_name or doc.kb_id),
                downloaded_by=ctx.payload.sub,
                is_batch=True,
                kb_dataset_id=doc.kb_dataset_id,
                kb_name=doc.kb_name,
            )

        return self._watermark_support.build_response(
            content=zip_buffer.getvalue(),
            filename=zip_filename,
            media_type="application/zip",
            distribution_mode="batch_zip",
            watermark=watermark,
        )

    def batch_download_ragflow_response(self, *, documents_info: list[dict], ctx):
        snapshot = ctx.snapshot
        assert_can_download(snapshot)

        if not documents_info:
            raise HTTPException(status_code=400, detail="no_documents_selected")

        documents: list[dict] = []
        for doc_info in documents_info:
            dataset = doc_info.get("dataset", DEFAULT_RAGFLOW_DATASET)
            assert_kb_allowed(snapshot, dataset)
            documents.append(
                {
                    "doc_id": doc_info.get("doc_id") or doc_info.get("id"),
                    "filename": doc_info.get("name", "unknown"),
                    "dataset": dataset,
                }
            )

        zip_content, filename = self._deps.ragflow_service.batch_download_documents(documents_info)
        if zip_content is None:
            raise HTTPException(status_code=500, detail=BATCH_DOWNLOAD_FAILED)

        watermark = self._watermark_support.build_watermark(
            ctx=ctx,
            purpose="batch_download",
            doc_id=f"ragflow-batch-{len(documents)}",
            filename=filename or f"ragflow_batch_{len(documents)}.zip",
            source="ragflow",
        )
        watermarked_zip = self._watermark_support.rewrite_zip_with_watermark(
            zip_content=zip_content,
            filename=filename or f"ragflow_batch_{len(documents)}.zip",
            source="ragflow",
            watermark=watermark,
            documents=documents,
        )

        for doc_info in documents_info:
            doc_id = doc_info.get("doc_id") or doc_info.get("id")
            dataset = doc_info.get("dataset", DEFAULT_RAGFLOW_DATASET)
            kb_info = resolve_kb_ref(self._deps, dataset)
            self._deps.download_log_store.log_download(
                doc_id=doc_id,
                filename=filename or "documents.zip",
                kb_id=(kb_info.dataset_id or dataset),
                downloaded_by=ctx.payload.sub,
                ragflow_doc_id=doc_id,
                is_batch=True,
                kb_dataset_id=kb_info.dataset_id,
                kb_name=(kb_info.name or dataset),
            )

        return self._watermark_support.build_response(
            content=watermarked_zip,
            filename=filename or "documents.zip",
            media_type="application/zip",
            distribution_mode="batch_zip",
            watermark=watermark,
        )
