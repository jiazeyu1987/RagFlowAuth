from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


DocumentSourceName = Literal["knowledge", "ragflow"]


@dataclass(frozen=True)
class DocumentRef:
    source: DocumentSourceName
    doc_id: str
    dataset_name: str | None = None  # ragflow only


@dataclass(frozen=True)
class DocumentBytes:
    filename: str
    content: bytes
    mime_type: str | None = None


@dataclass(frozen=True)
class DeleteResult:
    ok: bool
    message: str = ""
    ragflow_deleted: Optional[bool] = None
    ragflow_delete_error: Optional[str] = None

