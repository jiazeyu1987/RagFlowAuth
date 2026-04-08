from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from backend.services.documents.delete_actions import DocumentDeleteActions
from backend.services.documents.download_actions import DocumentDownloadActions
from backend.services.documents.models import DeleteResult, DocumentRef
from backend.services.documents.preview_support import DocumentPreviewSupport
from backend.services.documents.sources.knowledge_source import KnowledgeDocumentSource
from backend.services.documents.sources.ragflow_source import RagflowDocumentSource
from backend.services.documents.watermark_support import DocumentWatermarkSupport


@dataclass
class DocumentManager:
    deps: object

    def __post_init__(self) -> None:
        knowledge_source = KnowledgeDocumentSource(self.deps)
        ragflow_source = RagflowDocumentSource(self.deps)
        watermark_support = DocumentWatermarkSupport(self.deps)
        self._preview_support = DocumentPreviewSupport(
            deps=self.deps,
            knowledge_source=knowledge_source,
            ragflow_source=ragflow_source,
            watermark_support=watermark_support,
        )
        self._download_actions = DocumentDownloadActions(
            deps=self.deps,
            knowledge_source=knowledge_source,
            ragflow_source=ragflow_source,
            watermark_support=watermark_support,
        )
        self._delete_actions = DocumentDeleteActions(
            deps=self.deps,
            ragflow_source=ragflow_source,
        )

    def preview_payload(
        self,
        ref: DocumentRef,
        *,
        preview_filename: str | None = None,
        render: str = "default",
        ctx=None,
    ):
        return self._preview_support.preview_payload(
            ref,
            preview_filename=preview_filename,
            render=render,
            ctx=ctx,
        )

    def download_ragflow_response(self, *, doc_id: str, dataset: str, filename: str | None, ctx):
        return self._download_actions.download_ragflow_response(
            doc_id=doc_id,
            dataset=dataset,
            filename=filename,
            ctx=ctx,
        )

    def download_knowledge_response(self, *, doc_id: str, ctx):
        return self._download_actions.download_knowledge_response(doc_id=doc_id, ctx=ctx)

    def download_retired_knowledge_response(self, *, doc_id: str, ctx):
        return self._download_actions.download_retired_knowledge_response(doc_id=doc_id, ctx=ctx)

    def batch_download_knowledge_response(self, *, doc_ids: list[str], ctx):
        return self._download_actions.batch_download_knowledge_response(doc_ids=doc_ids, ctx=ctx)

    def batch_download_ragflow_response(self, *, documents_info: list[dict], ctx):
        return self._download_actions.batch_download_ragflow_response(documents_info=documents_info, ctx=ctx)

    async def stage_upload_knowledge(self, *, kb_ref: str, upload_file, ctx):
        from backend.services.knowledge_ingestion import KnowledgeIngestionError, KnowledgeIngestionManager

        ingestion_manager = getattr(self.deps, "knowledge_ingestion_manager", None)
        if ingestion_manager is None:
            ingestion_manager = KnowledgeIngestionManager(deps=self.deps)
        try:
            return await ingestion_manager.stage_upload_knowledge(kb_ref=kb_ref, upload_file=upload_file, ctx=ctx)
        except KnowledgeIngestionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    def delete_knowledge_document(self, *, doc_id: str, ctx) -> DeleteResult:
        return self._delete_actions.delete_knowledge_document(doc_id=doc_id, ctx=ctx)

    def delete_knowledge_document_trusted(
        self,
        *,
        doc_id: str,
        actor_user_id: str,
        actor_user=None,
        approval_request_id: str | None = None,
    ) -> DeleteResult:
        return self._delete_actions.delete_knowledge_document_trusted(
            doc_id=doc_id,
            actor_user_id=actor_user_id,
            actor_user=actor_user,
            approval_request_id=approval_request_id,
        )

    def delete_ragflow_document(self, *, doc_id: str, dataset_name: str, ctx) -> DeleteResult:
        return self._delete_actions.delete_ragflow_document(doc_id=doc_id, dataset_name=dataset_name, ctx=ctx)

    def assert_can_preview_knowledge(self, snapshot):
        self._preview_support.assert_can_preview_knowledge(snapshot)
