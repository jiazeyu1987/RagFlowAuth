from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class OperationApprovalWorkflowMemberBody(BaseModel):
    member_type: str
    member_ref: str


class OperationApprovalWorkflowStepBody(BaseModel):
    step_name: str
    members: list[OperationApprovalWorkflowMemberBody]


class OperationApprovalWorkflowBody(BaseModel):
    name: Optional[str] = None
    steps: list[OperationApprovalWorkflowStepBody]


class OperationApprovalActionBody(BaseModel):
    sign_token: str
    signature_meaning: str
    signature_reason: str
    notes: Optional[str] = None


class OperationApprovalWithdrawBody(BaseModel):
    reason: Optional[str] = None


class OperationApprovalRequestBrief(BaseModel):
    request_id: str
    operation_type: str
    operation_label: str
    status: str
    current_step_no: Optional[int] = None
    current_step_name: Optional[str] = None
    submitted_at_ms: int
    target_ref: Optional[str] = None
    target_label: Optional[str] = None
    applicant_user_id: Optional[str] = None
    applicant_username: Optional[str] = None
    summary: dict
    last_error: Optional[str] = None
