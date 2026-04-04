from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_OPERATION_TYPES = (
    "knowledge_file_upload",
    "knowledge_file_delete",
    "knowledge_base_create",
    "knowledge_base_delete",
)

INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW = "legacy_document_review"

OPERATION_TYPE_LABELS = {
    "knowledge_file_upload": "文件上传",
    "knowledge_file_delete": "文件删除",
    "knowledge_base_create": "知识库新建",
    "knowledge_base_delete": "知识库删除",
    INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW: "历史文档审核迁移",
}

WORKFLOW_MEMBER_TYPE_USER = "user"
WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE = "special_role"

SPECIAL_ROLE_DIRECT_MANAGER = "direct_manager"

SUPPORTED_WORKFLOW_MEMBER_TYPES = {
    WORKFLOW_MEMBER_TYPE_USER,
    WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
}

SUPPORTED_SPECIAL_ROLES = {
    SPECIAL_ROLE_DIRECT_MANAGER,
}

SPECIAL_ROLE_LABELS = {
    SPECIAL_ROLE_DIRECT_MANAGER: "直属主管",
}

REQUEST_STATUS_IN_APPROVAL = "in_approval"
REQUEST_STATUS_APPROVED_PENDING_EXECUTION = "approved_pending_execution"
REQUEST_STATUS_EXECUTING = "executing"
REQUEST_STATUS_EXECUTED = "executed"
REQUEST_STATUS_REJECTED = "rejected"
REQUEST_STATUS_WITHDRAWN = "withdrawn"
REQUEST_STATUS_EXECUTION_FAILED = "execution_failed"

SUPPORTED_REQUEST_STATUSES = {
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
    REQUEST_STATUS_EXECUTING,
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUS_WITHDRAWN,
    REQUEST_STATUS_EXECUTION_FAILED,
}

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

APPROVAL_RULE_ALL = "all"
APPROVAL_RULE_ANY = "any"
SUPPORTED_APPROVAL_RULES = {
    APPROVAL_RULE_ALL,
    APPROVAL_RULE_ANY,
}

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
