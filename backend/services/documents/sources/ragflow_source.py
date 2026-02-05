from __future__ import annotations

from backend.services.documents.errors import DocumentNotFound, DocumentSourceError
from backend.services.documents.models import DocumentBytes, DocumentRef


class RagflowDocumentSource:
    def __init__(self, deps):
        self._deps = deps

    def get_bytes(self, ref: DocumentRef) -> DocumentBytes:
        dataset = ref.dataset_name or "展厅"
        try:
            content, filename = self._deps.ragflow_service.download_document(ref.doc_id, dataset)
        except Exception as e:
            raise DocumentSourceError(str(e)) from e

        if content is None:
            raise DocumentNotFound("文档不存在或下载失败")
        return DocumentBytes(filename=filename or f"document_{ref.doc_id}", content=content)

    def delete(self, ref: DocumentRef) -> bool:
        dataset = ref.dataset_name or "展厅"
        try:
            return bool(self._deps.ragflow_service.delete_document(ref.doc_id, dataset_name=dataset))
        except Exception as e:
            raise DocumentSourceError(str(e)) from e

