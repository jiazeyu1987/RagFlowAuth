from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_OPERATION_TYPES = (
    "knowledge_file_upload",
    "knowledge_file_delete",
    "knowledge_base_create",
    "knowledge_base_delete",
    "document_control_revision_approval",
)

INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW = "legacy_document_review"
OPERATION_TYPE_DOCUMENT_CONTROL_REVISION_APPROVAL = "document_control_revision_approval"

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


@dataclass(slots=True)
class ApprovalWorkflowMemberRecord:
    member_type: str
    member_ref: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalWorkflowMemberRecord":
        return cls(
            member_type=str(data.get("member_type") or ""),
            member_ref=str(data.get("member_ref") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_type": self.member_type,
            "member_ref": self.member_ref,
        }


@dataclass(slots=True)
class ApprovalWorkflowStepRecord:
    step_no: int
    step_name: str
    members: list[ApprovalWorkflowMemberRecord] = field(default_factory=list)
    workflow_step_id: str | None = None
    approval_rule: str = APPROVAL_RULE_ALL
    created_at_ms: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalWorkflowStepRecord":
        return cls(
            workflow_step_id=(str(data["workflow_step_id"]) if data.get("workflow_step_id") else None),
            step_no=int(data.get("step_no") or 0),
            step_name=str(data.get("step_name") or ""),
            approval_rule=str(data.get("approval_rule") or APPROVAL_RULE_ALL),
            created_at_ms=(int(data["created_at_ms"]) if data.get("created_at_ms") is not None else None),
            members=[ApprovalWorkflowMemberRecord.from_dict(member) for member in (data.get("members") or [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_step_id": self.workflow_step_id,
            "step_no": self.step_no,
            "step_name": self.step_name,
            "approval_rule": self.approval_rule,
            "created_at_ms": self.created_at_ms,
            "members": [member.to_dict() for member in self.members],
        }


@dataclass(slots=True)
class ApprovalWorkflowRecord:
    operation_type: str
    name: str
    steps: list[ApprovalWorkflowStepRecord] = field(default_factory=list)
    is_active: bool = False
    created_at_ms: int | None = None
    updated_at_ms: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalWorkflowRecord":
        return cls(
            operation_type=str(data.get("operation_type") or ""),
            name=str(data.get("name") or ""),
            is_active=bool(data.get("is_active")),
            created_at_ms=(int(data["created_at_ms"]) if data.get("created_at_ms") is not None else None),
            updated_at_ms=(int(data["updated_at_ms"]) if data.get("updated_at_ms") is not None else None),
            steps=[ApprovalWorkflowStepRecord.from_dict(step) for step in (data.get("steps") or [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_type": self.operation_type,
            "name": self.name,
            "is_active": self.is_active,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(slots=True)
class ApprovalRequestApproverRecord:
    approver_user_id: str
    approver_username: str | None = None
    status: str = APPROVER_STATUS_PENDING
    action: str | None = None
    notes: Any = None
    signature_id: str | None = None
    acted_at_ms: int | None = None
    request_step_approver_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequestApproverRecord":
        return cls(
            request_step_approver_id=(
                str(data["request_step_approver_id"]) if data.get("request_step_approver_id") else None
            ),
            approver_user_id=str(data.get("approver_user_id") or ""),
            approver_username=(str(data["approver_username"]) if data.get("approver_username") else None),
            status=str(data.get("status") or APPROVER_STATUS_PENDING),
            action=(str(data["action"]) if data.get("action") else None),
            notes=data.get("notes"),
            signature_id=(str(data["signature_id"]) if data.get("signature_id") else None),
            acted_at_ms=(int(data["acted_at_ms"]) if data.get("acted_at_ms") is not None else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_step_approver_id": self.request_step_approver_id,
            "approver_user_id": self.approver_user_id,
            "approver_username": self.approver_username,
            "status": self.status,
            "action": self.action,
            "notes": self.notes,
            "signature_id": self.signature_id,
            "acted_at_ms": self.acted_at_ms,
        }


@dataclass(slots=True)
class ApprovalRequestStepRecord:
    step_no: int
    step_name: str
    approval_rule: str = APPROVAL_RULE_ALL
    status: str = STEP_STATUS_PENDING
    approvers: list[ApprovalRequestApproverRecord] = field(default_factory=list)
    request_step_id: str | None = None
    created_at_ms: int | None = None
    activated_at_ms: int | None = None
    completed_at_ms: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequestStepRecord":
        return cls(
            request_step_id=(str(data["request_step_id"]) if data.get("request_step_id") else None),
            step_no=int(data.get("step_no") or 0),
            step_name=str(data.get("step_name") or ""),
            approval_rule=str(data.get("approval_rule") or APPROVAL_RULE_ALL),
            status=str(data.get("status") or STEP_STATUS_PENDING),
            created_at_ms=(int(data["created_at_ms"]) if data.get("created_at_ms") is not None else None),
            activated_at_ms=(int(data["activated_at_ms"]) if data.get("activated_at_ms") is not None else None),
            completed_at_ms=(int(data["completed_at_ms"]) if data.get("completed_at_ms") is not None else None),
            approvers=[ApprovalRequestApproverRecord.from_dict(item) for item in (data.get("approvers") or [])],
        )

    def find_approver(self, approver_user_id: str) -> ApprovalRequestApproverRecord | None:
        clean_user_id = str(approver_user_id or "").strip()
        for approver in self.approvers:
            if approver.approver_user_id == clean_user_id:
                return approver
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_step_id": self.request_step_id,
            "step_no": self.step_no,
            "step_name": self.step_name,
            "approval_rule": self.approval_rule,
            "status": self.status,
            "created_at_ms": self.created_at_ms,
            "activated_at_ms": self.activated_at_ms,
            "completed_at_ms": self.completed_at_ms,
            "approvers": [approver.to_dict() for approver in self.approvers],
        }


@dataclass(slots=True)
class ApprovalRequestEventRecord:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str | None = None
    actor_user_id: str | None = None
    actor_username: str | None = None
    step_no: int | None = None
    created_at_ms: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequestEventRecord":
        return cls(
            event_id=(str(data["event_id"]) if data.get("event_id") else None),
            event_type=str(data.get("event_type") or ""),
            actor_user_id=(str(data["actor_user_id"]) if data.get("actor_user_id") else None),
            actor_username=(str(data["actor_username"]) if data.get("actor_username") else None),
            step_no=(int(data["step_no"]) if data.get("step_no") is not None else None),
            payload=dict(data.get("payload") or {}),
            created_at_ms=(int(data["created_at_ms"]) if data.get("created_at_ms") is not None else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor_user_id": self.actor_user_id,
            "actor_username": self.actor_username,
            "step_no": self.step_no,
            "payload": dict(self.payload),
            "created_at_ms": self.created_at_ms,
        }


@dataclass(slots=True)
class ApprovalRequestArtifactRecord:
    artifact_type: str
    file_path: str
    artifact_id: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    created_at_ms: int | None = None
    cleaned_at_ms: int | None = None
    cleanup_status: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequestArtifactRecord":
        return cls(
            artifact_id=(str(data["artifact_id"]) if data.get("artifact_id") else None),
            artifact_type=str(data.get("artifact_type") or ""),
            file_path=str(data.get("file_path") or ""),
            file_name=(str(data["file_name"]) if data.get("file_name") else None),
            mime_type=(str(data["mime_type"]) if data.get("mime_type") else None),
            size_bytes=(int(data["size_bytes"]) if data.get("size_bytes") is not None else None),
            sha256=(str(data["sha256"]) if data.get("sha256") else None),
            meta=dict(data.get("meta") or {}),
            created_at_ms=(int(data["created_at_ms"]) if data.get("created_at_ms") is not None else None),
            cleaned_at_ms=(int(data["cleaned_at_ms"]) if data.get("cleaned_at_ms") is not None else None),
            cleanup_status=(str(data["cleanup_status"]) if data.get("cleanup_status") else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "meta": dict(self.meta),
            "created_at_ms": self.created_at_ms,
            "cleaned_at_ms": self.cleaned_at_ms,
            "cleanup_status": self.cleanup_status,
        }


@dataclass(slots=True)
class ApprovalRequestRecord:
    request_id: str
    operation_type: str
    workflow_name: str
    status: str
    applicant_user_id: str
    applicant_username: str
    summary: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    workflow_snapshot: dict[str, Any] = field(default_factory=dict)
    steps: list[ApprovalRequestStepRecord] = field(default_factory=list)
    events: list[ApprovalRequestEventRecord] = field(default_factory=list)
    artifacts: list[ApprovalRequestArtifactRecord] = field(default_factory=list)
    target_ref: str | None = None
    target_label: str | None = None
    current_step_no: int | None = None
    current_step_name: str | None = None
    submitted_at_ms: int = 0
    completed_at_ms: int | None = None
    execution_started_at_ms: int | None = None
    executed_at_ms: int | None = None
    last_error: str | None = None
    company_id: int | None = None
    department_id: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequestRecord":
        return cls(
            request_id=str(data.get("request_id") or ""),
            operation_type=str(data.get("operation_type") or ""),
            workflow_name=str(data.get("workflow_name") or ""),
            status=str(data.get("status") or ""),
            applicant_user_id=str(data.get("applicant_user_id") or ""),
            applicant_username=str(data.get("applicant_username") or ""),
            summary=dict(data.get("summary") or {}),
            payload=dict(data.get("payload") or {}),
            result=dict(data.get("result") or {}),
            workflow_snapshot=dict(data.get("workflow_snapshot") or {}),
            steps=[ApprovalRequestStepRecord.from_dict(step) for step in (data.get("steps") or [])],
            events=[ApprovalRequestEventRecord.from_dict(event) for event in (data.get("events") or [])],
            artifacts=[ApprovalRequestArtifactRecord.from_dict(item) for item in (data.get("artifacts") or [])],
            target_ref=(str(data["target_ref"]) if data.get("target_ref") else None),
            target_label=(str(data["target_label"]) if data.get("target_label") else None),
            current_step_no=(int(data["current_step_no"]) if data.get("current_step_no") is not None else None),
            current_step_name=(str(data["current_step_name"]) if data.get("current_step_name") else None),
            submitted_at_ms=int(data.get("submitted_at_ms") or 0),
            completed_at_ms=(int(data["completed_at_ms"]) if data.get("completed_at_ms") is not None else None),
            execution_started_at_ms=(
                int(data["execution_started_at_ms"]) if data.get("execution_started_at_ms") is not None else None
            ),
            executed_at_ms=(int(data["executed_at_ms"]) if data.get("executed_at_ms") is not None else None),
            last_error=(str(data["last_error"]) if data.get("last_error") else None),
            company_id=(int(data["company_id"]) if data.get("company_id") is not None else None),
            department_id=(int(data["department_id"]) if data.get("department_id") is not None else None),
        )

    def find_step(self, step_no: int) -> ApprovalRequestStepRecord | None:
        target_step_no = int(step_no)
        for step in self.steps:
            if step.step_no == target_step_no:
                return step
        return None

    def next_step_after(self, current_step_no: int) -> ApprovalRequestStepRecord | None:
        for step in self.steps:
            if step.step_no > int(current_step_no):
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "operation_type": self.operation_type,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "applicant_user_id": self.applicant_user_id,
            "applicant_username": self.applicant_username,
            "target_ref": self.target_ref,
            "target_label": self.target_label,
            "summary": dict(self.summary),
            "payload": dict(self.payload),
            "result": dict(self.result),
            "workflow_snapshot": dict(self.workflow_snapshot),
            "current_step_no": self.current_step_no,
            "current_step_name": self.current_step_name,
            "submitted_at_ms": self.submitted_at_ms,
            "completed_at_ms": self.completed_at_ms,
            "execution_started_at_ms": self.execution_started_at_ms,
            "executed_at_ms": self.executed_at_ms,
            "last_error": self.last_error,
            "company_id": self.company_id,
            "department_id": self.department_id,
            "steps": [step.to_dict() for step in self.steps],
            "events": [event.to_dict() for event in self.events],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


@dataclass(slots=True)
class ApprovalOutcomeProjection:
    approval_rule: str
    remaining_after_this: int
    next_step: ApprovalRequestStepRecord | None
    after_status: str


@dataclass(slots=True)
class ApprovalStateTransition:
    request_data: ApprovalRequestRecord
    execute_request: bool
    notify_step_started: bool
