from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_OPERATION_TYPES = (
    "knowledge_file_upload",
    "knowledge_file_delete",
    "knowledge_base_create",
    "knowledge_base_delete",
)

OPERATION_TYPE_LABELS = {
    "knowledge_file_upload": "文件上传",
    "knowledge_file_delete": "文件删除",
    "knowledge_base_create": "知识库新建",
    "knowledge_base_delete": "知识库删除",
}

REQUEST_STATUS_IN_APPROVAL = "in_approval"
REQUEST_STATUS_APPROVED_PENDING_EXECUTION = "approved_pending_execution"
REQUEST_STATUS_EXECUTING = "executing"
REQUEST_STATUS_EXECUTED = "executed"
REQUEST_STATUS_REJECTED = "rejected"
REQUEST_STATUS_WITHDRAWN = "withdrawn"
REQUEST_STATUS_EXECUTION_FAILED = "execution_failed"

TERMINAL_REQUEST_STATUSES = {
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUS_WITHDRAWN,
    REQUEST_STATUS_EXECUTION_FAILED,
}

STEP_STATUS_PENDING = "pending"
STEP_STATUS_ACTIVE = "active"
STEP_STATUS_APPROVED = "approved"
STEP_STATUS_REJECTED = "rejected"

APPROVER_STATUS_PENDING = "pending"
APPROVER_STATUS_APPROVED = "approved"
APPROVER_STATUS_REJECTED = "rejected"


@dataclass
class OperationApprovalArtifact:
    artifact_type: str
    file_path: str
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreparedOperationRequest:
    operation_type: str
    payload: dict[str, Any]
    summary: dict[str, Any]
    target_ref: str | None = None
    target_label: str | None = None
    artifacts: list[OperationApprovalArtifact] = field(default_factory=list)


@dataclass
class OperationExecutionError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code
