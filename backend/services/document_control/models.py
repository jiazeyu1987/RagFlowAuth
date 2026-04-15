from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ControlledRevision:
    controlled_revision_id: str
    controlled_document_id: str
    kb_doc_id: str
    revision_no: int
    status: str
    change_summary: str | None
    previous_revision_id: str | None
    approval_request_id: str | None
    approval_last_request_id: str | None
    approval_round: int
    approval_submitted_at_ms: int | None
    approval_completed_at_ms: int | None
    current_approval_step_no: int | None
    current_approval_step_name: str | None
    current_approval_step_timeout_reminder_minutes: int | None
    current_approval_step_overdue_at_ms: int | None
    current_approval_step_last_reminded_at_ms: int | None
    release_mode: str | None
    release_manual_archive_completed_by: str | None
    release_manual_archive_completed_at_ms: int | None
    approved_by: str | None
    approved_at_ms: int | None
    effective_at_ms: int | None
    obsolete_at_ms: int | None
    obsolete_requested_by: str | None
    obsolete_requested_at_ms: int | None
    obsolete_reason: str | None
    obsolete_retention_until_ms: int | None
    obsolete_approved_by: str | None
    obsolete_approved_at_ms: int | None
    destruction_confirmed_by: str | None
    destruction_confirmed_at_ms: int | None
    destruction_notes: str | None
    superseded_at_ms: int | None
    superseded_by_revision_id: str | None
    created_by: str
    created_at_ms: int
    updated_at_ms: int
    filename: str
    file_size: int
    mime_type: str
    uploaded_by: str
    uploaded_at_ms: int
    reviewed_by: str | None
    reviewed_at_ms: int | None
    review_notes: str | None
    ragflow_doc_id: str | None
    kb_id: str
    kb_dataset_id: str | None
    kb_name: str | None
    file_sha256: str | None
    file_path: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ControlledDocument:
    controlled_document_id: str
    doc_code: str
    title: str
    document_type: str
    product_name: str | None
    registration_ref: str | None
    target_kb_id: str
    target_kb_name: str | None
    distribution_department_ids: list[int] | None
    current_revision_id: str | None
    effective_revision_id: str | None
    created_by: str
    created_at_ms: int
    updated_at_ms: int
    current_revision: ControlledRevision | None = None
    effective_revision: ControlledRevision | None = None
    revisions: list[ControlledRevision] | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
