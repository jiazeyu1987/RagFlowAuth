from __future__ import annotations

from abc import ABC, abstractmethod

from backend.services.documents.models import DocumentBytes, DocumentRef


class DocumentSource(ABC):
    @abstractmethod
    def get_bytes(self, ref: DocumentRef) -> DocumentBytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, ref: DocumentRef) -> bool:
        raise NotImplementedError

