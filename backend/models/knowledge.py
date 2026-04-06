from typing import Any

from pydantic import BaseModel

from backend.models.contracts import LooseObjectModel
from backend.models.operation_approval import OperationApprovalRequestEnvelope


class DatasetEnvelope(BaseModel):
    dataset: LooseObjectModel


class DatasetListEnvelope(BaseModel):
    datasets: list[LooseObjectModel]
    count: int


class KnowledgeDirectoryTree(BaseModel):
    nodes: list[LooseObjectModel]
    datasets: list[LooseObjectModel]
    bindings: dict[str, Any]


class KnowledgeDirectoryNodeEnvelope(BaseModel):
    node: LooseObjectModel


class KnowledgeDirectoryDeleteResult(BaseModel):
    message: str
    node_id: str


class KnowledgeDirectoryDeleteResultEnvelope(BaseModel):
    result: KnowledgeDirectoryDeleteResult


class KnowledgeDirectoryAssignmentResult(BaseModel):
    message: str
    dataset_id: str
    node_id: str | None


class KnowledgeDirectoryAssignmentResultEnvelope(BaseModel):
    result: KnowledgeDirectoryAssignmentResult


class UploadAllowedExtensionsResponse(BaseModel):
    allowed_extensions: list[str]
    updated_at_ms: int


class KnowledgeDeletionRecord(BaseModel):
    id: int
    doc_id: str
    filename: str
    kb_id: str
    deleted_by: str | None = None
    deleted_by_name: str | None = None
    deleted_at_ms: int
    original_uploader: str | None = None
    original_uploader_name: str | None = None
    original_reviewer: str | None = None
    original_reviewer_name: str | None = None
    ragflow_doc_id: str | None = None


class KnowledgeDeletionListEnvelope(BaseModel):
    deletions: list[KnowledgeDeletionRecord]
    count: int
