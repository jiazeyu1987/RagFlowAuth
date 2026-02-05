from __future__ import annotations

import os

from backend.services.documents.errors import DocumentNotFound, DocumentSourceError
from backend.services.documents.models import DocumentBytes, DocumentRef


class KnowledgeDocumentSource:
    def __init__(self, deps):
        self._deps = deps

    def get_bytes(self, ref: DocumentRef) -> DocumentBytes:
        doc = self._deps.kb_store.get_document(ref.doc_id)
        if not doc:
            raise DocumentNotFound("文档不存在")
        if not os.path.exists(doc.file_path):
            raise DocumentNotFound("文件不存在")
        try:
            with open(doc.file_path, "rb") as f:
                content = f.read()
        except Exception as e:
            raise DocumentSourceError(str(e)) from e
        return DocumentBytes(filename=doc.filename, content=content, mime_type=getattr(doc, "mime_type", None))

    def delete(self, ref: DocumentRef) -> bool:
        # Local delete is managed by DocumentManager because it needs logging and DB cleanup.
        # This method only deletes the kb_store record.
        try:
            return bool(self._deps.kb_store.delete_document(ref.doc_id))
        except Exception as e:
            raise DocumentSourceError(str(e)) from e
