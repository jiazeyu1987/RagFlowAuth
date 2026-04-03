from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class KbDocument:
    doc_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by: str
    status: str
    uploaded_at_ms: int
    reviewed_by: Optional[str] = None
    reviewed_at_ms: Optional[int] = None
    review_notes: Optional[str] = None
    ragflow_doc_id: Optional[str] = None
    kb_id: str = "展厅"
    kb_dataset_id: Optional[str] = None
    kb_name: Optional[str] = None
    logical_doc_id: Optional[str] = None
    version_no: int = 1
    previous_doc_id: Optional[str] = None
    superseded_by_doc_id: Optional[str] = None
    is_current: bool = True
    effective_status: Optional[str] = None
    archived_at_ms: Optional[int] = None
    retention_until_ms: Optional[int] = None
    file_sha256: Optional[str] = None
    retired_by: Optional[str] = None
    retirement_reason: Optional[str] = None
    archive_manifest_path: Optional[str] = None
    archive_package_path: Optional[str] = None
    archive_package_sha256: Optional[str] = None
