from pydantic import BaseModel
from typing import Optional, List


class DocumentResponse(BaseModel):
    """Document response model"""
    doc_id: str
    filename: str
    file_size: int
    mime_type: str
    uploaded_by: str
    status: str
    uploaded_at_ms: int
    reviewed_by: Optional[str] = None
    reviewed_at_ms: Optional[int] = None
    review_notes: Optional[str] = None
    ragflow_doc_id: Optional[str] = None
    kb_id: str
    signature_id: Optional[str] = None
    signed_at_ms: Optional[int] = None
    logical_doc_id: Optional[str] = None
    version_no: Optional[int] = 1
    previous_doc_id: Optional[str] = None
    superseded_by_doc_id: Optional[str] = None
    is_current: Optional[bool] = True
    effective_status: Optional[str] = None
    archived_at_ms: Optional[int] = None
    retention_until_ms: Optional[int] = None
    file_sha256: Optional[str] = None
    retired_by: Optional[str] = None
    retirement_reason: Optional[str] = None
    archive_manifest_path: Optional[str] = None
    archive_package_path: Optional[str] = None
    archive_package_sha256: Optional[str] = None

class BatchDownloadRequest(BaseModel):
    """Batch download request model"""
    doc_ids: List[str]
