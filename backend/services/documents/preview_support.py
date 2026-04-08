from __future__ import annotations

import logging
import time

from backend.app.core.permission_resolver import assert_can_download, assert_can_review
from backend.app.core.request_id import get_request_id
from backend.services.documents.models import DocumentRef

logger = logging.getLogger("backend.services.documents.document_manager")


class DocumentPreviewSupport:
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

    def preview_payload(
        self,
        ref: DocumentRef,
        *,
        preview_filename: str | None = None,
        render: str = "default",
        ctx=None,
    ):
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
            payload["watermark"] = self._watermark_support.build_watermark(
                ctx=ctx,
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

    def assert_can_preview_knowledge(self, snapshot):
        try:
            assert_can_download(snapshot)
        except Exception:
            assert_can_review(snapshot)
