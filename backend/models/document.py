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
    approval_status: Optional[str] = None
    current_step_no: Optional[int] = None
    current_step_name: Optional[str] = None
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


class DocumentReviewRequest(BaseModel):
    """Document review request model"""
    sign_token: str
    signature_meaning: str
    signature_reason: str
    review_notes: Optional[str] = None


class BatchDocumentReviewRequest(BaseModel):
    """Batch document review request model"""
    doc_ids: List[str]
    sign_token: str
    signature_meaning: str
    signature_reason: str
    review_notes: Optional[str] = None


class DocumentOverwriteReviewRequest(BaseModel):
    replace_doc_id: str
    sign_token: str
    signature_meaning: str
    signature_reason: str
    review_notes: Optional[str] = None


class BatchDocumentReviewResponse(BaseModel):
    """Batch document review response model"""
    total: int
    success_count: int
    failed_count: int
    succeeded_doc_ids: List[str]
    failed_items: List[dict]


class StatsResponse(BaseModel):
    """Statistics response model"""
    total_documents: int
    pending_documents: int
    approved_documents: int
    rejected_documents: int


class BatchDownloadRequest(BaseModel):
    """Batch download request model"""
    doc_ids: List[str]
