from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.database.sqlite import connect_sqlite
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.compliance.retired_records import RetiredRecordsService
from backend.services.document_control.models import ControlledDocument, ControlledRevision
from backend.services.knowledge_ingestion import KnowledgeIngestionManager
from backend.services.notification import NotificationManagerError
from backend.services.operation_approval.decision_service import OperationApprovalDecisionService
from backend.services.operation_approval.store import OperationApprovalStore
from backend.services.operation_approval.types import (
    REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_REJECTED,
)
from backend.services.training_compliance_support import TrainingComplianceError


REVISION_STATUS_DRAFT = "draft"
REVISION_STATUS_APPROVAL_IN_PROGRESS = "approval_in_progress"
REVISION_STATUS_APPROVAL_REJECTED = "approval_rejected"
REVISION_STATUS_APPROVED_PENDING_EFFECTIVE = "approved_pending_effective"
REVISION_STATUS_EFFECTIVE = "effective"
REVISION_STATUS_OBSOLETE = "obsolete"
REVISION_STATUS_SUPERSEDED = "superseded"

RELEASE_MODE_AUTOMATIC = "automatic"
RELEASE_MODE_MANUAL_BY_DOC_CONTROL = "manual_by_doc_control"
ALLOWED_RELEASE_MODES = {RELEASE_MODE_AUTOMATIC, RELEASE_MODE_MANUAL_BY_DOC_CONTROL}

OPERATION_TYPE_DOCUMENT_CONTROL_REVISION_APPROVAL = "document_control_revision_approval"
WORKFLOW_STEP_TYPE_COSIGN = "cosign"
WORKFLOW_STEP_TYPE_APPROVE = "approve"
WORKFLOW_STEP_TYPE_STANDARDIZE_REVIEW = "standardize_review"
WORKFLOW_STEP_SEQUENCE = (
    WORKFLOW_STEP_TYPE_COSIGN,
    WORKFLOW_STEP_TYPE_APPROVE,
    WORKFLOW_STEP_TYPE_STANDARDIZE_REVIEW,
)

DEPARTMENT_ACK_STATUS_PENDING = "pending"
DEPARTMENT_ACK_STATUS_CONFIRMED = "confirmed"
DEPARTMENT_ACK_STATUS_OVERDUE = "overdue"
DEPARTMENT_ACK_STATUSES = {
    DEPARTMENT_ACK_STATUS_PENDING,
    DEPARTMENT_ACK_STATUS_CONFIRMED,
    DEPARTMENT_ACK_STATUS_OVERDUE,
}
DEPARTMENT_ACK_DUE_DAYS_DEFAULT = 7

NOTIFICATION_EVENT_DOC_CTRL_DEPT_ACK_REQUIRED = "document_control_department_ack_required"
NOTIFICATION_EVENT_DOC_CTRL_DEPT_ACK_OVERDUE = "document_control_department_ack_overdue"
NOTIFICATION_EVENT_DOC_CTRL_APPROVAL_STEP_OVERDUE = "document_control_approval_step_overdue"


@dataclass
class DocumentControlError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class DocumentControlService:
    def __init__(self, *, deps: Any):
        self._deps = deps
        kb_store = getattr(deps, "kb_store", None)
        db_path = str(getattr(kb_store, "db_path", "") or "").strip()
        if not db_path:
            raise DocumentControlError("document_control_db_path_missing", status_code=500)
        self._db_path = Path(db_path).resolve()
        self._approval_store = OperationApprovalStore(str(self._db_path))
        self._approval_decision_service = OperationApprovalDecisionService(
            store=self._approval_store,
            error_factory=lambda code, status_code=400: DocumentControlError(code, status_code=status_code),
        )

    @classmethod
    def from_deps(cls, deps: Any) -> "DocumentControlService":
        return cls(deps=deps)

    def _connect(self):
        return connect_sqlite(self._db_path)

    @staticmethod
    def _map_integrity_error(exc: sqlite3.IntegrityError) -> DocumentControlError:
        message = str(exc).lower()
        if "controlled_documents.doc_code" in message or "idx_controlled_documents_doc_code" in message:
            return DocumentControlError("doc_code_conflict", status_code=409)
        if "controlled_revisions.controlled_document_id, controlled_revisions.revision_no" in message:
            return DocumentControlError("revision_no_conflict", status_code=409)
        if "idx_controlled_revisions_doc_revision_no" in message:
            return DocumentControlError("revision_no_conflict", status_code=409)
        if "idx_controlled_revisions_one_effective" in message:
            return DocumentControlError("effective_revision_conflict", status_code=409)
        return DocumentControlError("document_control_conflict", status_code=409)

    @staticmethod
    def _require_text(value: str | None, code: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise DocumentControlError(code)
        return text

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _to_json_text(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _normalize_department_ids(department_ids: list[object] | None) -> list[int]:
        out: list[int] = []
        seen: set[int] = set()
        for raw in department_ids or []:
            try:
                department_id = int(raw)
            except Exception as exc:  # noqa: BLE001
                raise DocumentControlError("invalid_department_id") from exc
            if department_id <= 0:
                raise DocumentControlError("invalid_department_id")
            if department_id in seen:
                continue
            seen.add(department_id)
            out.append(department_id)
        out.sort()
        return out

    @staticmethod
    def _parse_distribution_department_ids_json(value: str | None) -> list[int]:
        raw = str(value or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            raise DocumentControlError("document_control_distribution_departments_invalid", status_code=500) from exc
        if parsed is None:
            return []
        if not isinstance(parsed, list):
            raise DocumentControlError("document_control_distribution_departments_invalid", status_code=500)
        return DocumentControlService._normalize_department_ids(parsed)

    def _load_distribution_department_ids(self, conn, *, controlled_document_id: str) -> list[int]:
        row = conn.execute(
            """
            SELECT distribution_department_ids_json
            FROM controlled_documents
            WHERE controlled_document_id = ?
            """,
            (controlled_document_id,),
        ).fetchone()
        if row is None:
            raise DocumentControlError("controlled_document_not_found", status_code=404)
        return self._parse_distribution_department_ids_json(row["distribution_department_ids_json"])

    def _update_distribution_department_ids(
        self,
        conn,
        *,
        controlled_document_id: str,
        department_ids: list[int],
        now_ms: int,
    ) -> None:
        cur = conn.execute(
            """
            UPDATE controlled_documents
            SET distribution_department_ids_json = ?,
                updated_at_ms = ?
            WHERE controlled_document_id = ?
            """,
            (self._to_json_text(department_ids), now_ms, controlled_document_id),
        )
        if int(cur.rowcount or 0) <= 0:
            raise DocumentControlError("controlled_document_not_found", status_code=404)

    def list_document_type_workflows(self) -> list[dict[str, object]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT document_type
                FROM document_control_approval_workflows
                WHERE is_active = 1
                ORDER BY document_type ASC
                """
            ).fetchall()
            return [self.get_document_type_workflow(document_type=str(row["document_type"]), conn=conn) for row in rows]
        finally:
            conn.close()

    def get_document_type_workflow(self, *, document_type: str, conn=None) -> dict[str, object]:
        clean_type = self._require_text(document_type, "document_type_required").lower()
        owns_conn = False
        if conn is None:
            conn = self._connect()
            owns_conn = True
        try:
            row = conn.execute(
                """
                SELECT document_type, name, is_active, created_at_ms, updated_at_ms
                FROM document_control_approval_workflows
                WHERE document_type = ?
                """,
                (clean_type,),
            ).fetchone()
            if row is None or not bool(int(row["is_active"] or 0)):
                raise DocumentControlError("document_control_workflow_not_configured", status_code=409)
            step_rows = conn.execute(
                """
                SELECT workflow_step_id, step_no, step_type, approval_rule, member_source, timeout_reminder_minutes, created_at_ms
                FROM document_control_approval_workflow_steps
                WHERE document_type = ?
                ORDER BY step_no ASC
                """,
                (clean_type,),
            ).fetchall()
            steps: list[dict[str, object]] = []
            for step_row in step_rows:
                approver_rows = conn.execute(
                    """
                    SELECT approver_user_id
                    FROM document_control_approval_step_approvers
                    WHERE workflow_step_id = ?
                    ORDER BY approver_user_id ASC
                    """,
                    (str(step_row["workflow_step_id"]),),
                ).fetchall()
                steps.append(
                    {
                        "workflow_step_id": str(step_row["workflow_step_id"]),
                        "step_no": int(step_row["step_no"] or 0),
                        "step_type": str(step_row["step_type"] or "").strip().lower(),
                        "approval_rule": str(step_row["approval_rule"] or "").strip().lower(),
                        "member_source": str(step_row["member_source"] or "").strip(),
                        "timeout_reminder_minutes": int(step_row["timeout_reminder_minutes"] or 0),
                        "approver_user_ids": [str(item["approver_user_id"]) for item in approver_rows if item],
                    }
                )
            return {
                "document_type": clean_type,
                "name": str(row["name"] or ""),
                "is_active": bool(int(row["is_active"] or 0)),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
                "steps": steps,
            }
        finally:
            if owns_conn:
                conn.close()

    def upsert_document_type_workflow(
        self,
        *,
        document_type: str,
        name: str | None,
        steps: list[dict[str, object]],
    ) -> dict[str, object]:
        clean_type = self._require_text(document_type, "document_type_required").lower()
        workflow_name = self._require_text(name or f"document_control_{clean_type}_approval", "workflow_name_required")
        normalized_steps = self._normalize_persisted_workflow_steps(steps=steps)
        now_ms = self._now_ms()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO document_control_approval_workflows (
                    document_type,
                    name,
                    is_active,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(document_type) DO UPDATE SET
                    name = excluded.name,
                    is_active = 1,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (clean_type, workflow_name, now_ms, now_ms),
            )
            conn.execute("DELETE FROM document_control_approval_step_approvers WHERE document_type = ?", (clean_type,))
            conn.execute("DELETE FROM document_control_approval_workflow_steps WHERE document_type = ?", (clean_type,))
            for item in normalized_steps:
                step_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO document_control_approval_workflow_steps (
                        workflow_step_id,
                        document_type,
                        step_no,
                        step_type,
                        approval_rule,
                        member_source,
                        timeout_reminder_minutes,
                        created_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step_id,
                        clean_type,
                        int(item["step_no"]),
                        str(item["step_type"]),
                        str(item["approval_rule"]),
                        str(item["member_source"]),
                        int(item["timeout_reminder_minutes"]),
                        now_ms,
                    ),
                )
                for approver_user_id in item["approver_user_ids"]:
                    conn.execute(
                        """
                        INSERT INTO document_control_approval_step_approvers (
                            workflow_step_approver_id,
                            workflow_step_id,
                            document_type,
                            step_no,
                            approver_user_id,
                            created_at_ms
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            step_id,
                            clean_type,
                            int(item["step_no"]),
                            str(approver_user_id),
                            now_ms,
                        ),
                    )
            conn.commit()
            return self.get_document_type_workflow(document_type=clean_type, conn=conn)
        finally:
            conn.close()

    def _normalize_persisted_workflow_steps(self, *, steps: list[dict[str, object]]) -> list[dict[str, object]]:
        if not isinstance(steps, list) or not steps:
            raise DocumentControlError("document_control_workflow_steps_required", status_code=409)
        normalized: list[dict[str, object]] = []
        for index, raw_step in enumerate(steps, start=1):
            if not isinstance(raw_step, dict):
                raise DocumentControlError("document_control_workflow_step_invalid", status_code=409)
            step_type = str(raw_step.get("step_type") or "").strip().lower()
            if step_type not in WORKFLOW_STEP_SEQUENCE:
                raise DocumentControlError("document_control_workflow_step_type_invalid", status_code=409)
            approval_rule = str(raw_step.get("approval_rule") or "").strip().lower()
            if approval_rule not in {"all", "any"}:
                raise DocumentControlError("document_control_workflow_approval_rule_invalid", status_code=409)
            member_source = str(raw_step.get("member_source") or "").strip() or "fixed"
            timeout_reminder_minutes = raw_step.get("timeout_reminder_minutes")
            try:
                timeout_reminder_minutes = int(timeout_reminder_minutes)
            except (TypeError, ValueError):
                raise DocumentControlError("document_control_workflow_timeout_invalid", status_code=409) from None
            if timeout_reminder_minutes <= 0:
                raise DocumentControlError("document_control_workflow_timeout_invalid", status_code=409)
            approver_user_ids = raw_step.get("approver_user_ids")
            if not isinstance(approver_user_ids, list) or not approver_user_ids:
                raise DocumentControlError("document_control_workflow_approvers_required", status_code=409)
            clean_approvers: list[str] = []
            seen: set[str] = set()
            for raw_user_id in approver_user_ids:
                user_id = str(raw_user_id or "").strip()
                if not user_id:
                    raise DocumentControlError("document_control_workflow_approver_invalid", status_code=409)
                if user_id in seen:
                    raise DocumentControlError("document_control_workflow_approver_duplicated", status_code=409)
                self._resolve_active_user(user_id=user_id)
                clean_approvers.append(user_id)
                seen.add(user_id)
            normalized.append(
                {
                    "step_no": index,
                    "step_type": step_type,
                    "approval_rule": approval_rule,
                    "member_source": member_source,
                    "timeout_reminder_minutes": timeout_reminder_minutes,
                    "approver_user_ids": clean_approvers,
                }
            )
        if tuple(item["step_type"] for item in normalized) != WORKFLOW_STEP_SEQUENCE:
            raise DocumentControlError("document_control_workflow_step_sequence_invalid", status_code=409)
        return normalized

    def _list_active_user_ids_for_department(self, conn, *, department_id: int) -> list[str]:
        target_department_id = int(department_id)
        candidate_stores = [
            self._require_user_store(),
            getattr(self._deps, "user_store", None),
        ]
        for store in candidate_stores:
            list_users = getattr(store, "list_users", None)
            if not callable(list_users):
                continue
            rows = list_users(status="active", limit=1000) or []
            result: list[str] = []
            for row in rows:
                user_department_id = getattr(row, "department_id", None)
                try:
                    normalized_department_id = int(user_department_id) if user_department_id is not None else None
                except Exception:
                    normalized_department_id = None
                if normalized_department_id != target_department_id:
                    continue
                user_id = str(getattr(row, "user_id", "") or "").strip()
                if not user_id:
                    continue
                result.append(user_id)
            if result:
                return sorted(set(result))

        rows = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE status = 'active'
              AND department_id = ?
            ORDER BY user_id ASC
            """,
            (target_department_id,),
        ).fetchall()
        return [str(row["user_id"]) for row in rows if row and str(row["user_id"] or "").strip()]

    def _require_notification_manager(self):
        manager = getattr(self._deps, "notification_manager", None) or getattr(self._deps, "notification_service", None)
        if manager is None or not callable(getattr(manager, "notify_event", None)):
            raise DocumentControlError("document_control_notification_manager_unavailable", status_code=500)
        return manager

    @staticmethod
    def _require_pdf_upload(*, filename: str, mime_type: str) -> None:
        clean_name = str(filename or "").strip().lower()
        clean_mime = str(mime_type or "").strip().lower()
        if not clean_name.endswith(".pdf") or clean_mime != "application/pdf":
            raise DocumentControlError("document_control_pdf_required", status_code=400)

    @staticmethod
    def _safe_segment(value: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in str(value or "").strip())
        return safe or "controlled_document"

    def _staged_file_path(self, *, doc_code: str, revision_no: int, upload_filename: str) -> tuple[str, Path]:
        display_name, relative_path = KnowledgeIngestionManager._normalize_relative_upload_path(upload_filename)
        root = resolve_repo_path(settings.UPLOAD_DIR) / "document_control" / self._safe_segment(doc_code) / f"v{revision_no:03d}"
        final_path = root / relative_path
        return display_name, final_path

    @staticmethod
    def _detect_mime(filename: str, content_type: str | None) -> str:
        return KnowledgeIngestionManager._detect_mime(filename, content_type)

    @staticmethod
    def _write_upload(*, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _resolve_kb_info(self, target_kb_id: str) -> tuple[str, str | None, str | None]:
        kb_info = resolve_kb_ref(self._deps, target_kb_id)
        kb_id = str(kb_info.dataset_id or target_kb_id).strip()
        kb_dataset_id = str(kb_info.dataset_id).strip() if kb_info.dataset_id else None
        kb_name = str(kb_info.name).strip() if kb_info.name else str(target_kb_id).strip()
        return kb_id, kb_dataset_id, kb_name

    def _create_kb_document(
        self,
        *,
        controlled_document_id: str,
        revision_no: int,
        file_path: Path,
        filename: str,
        mime_type: str,
        uploaded_by: str,
        kb_id: str,
        kb_dataset_id: str | None,
        kb_name: str | None,
        previous_doc_id: str | None,
        is_current: bool,
        ):
        return self._deps.kb_store.create_document(
            filename=filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
            kb_id=kb_id,
            kb_dataset_id=kb_dataset_id,
            kb_name=kb_name,
            status="draft",
            logical_doc_id=controlled_document_id,
            version_no=revision_no,
            previous_doc_id=previous_doc_id,
            is_current=is_current,
            effective_status="draft",
        )

    def _revision_from_joined_row(self, row) -> ControlledRevision:
        return ControlledRevision(
            controlled_revision_id=str(row["controlled_revision_id"]),
            controlled_document_id=str(row["controlled_document_id"]),
            kb_doc_id=str(row["kb_doc_id"]),
            revision_no=int(row["revision_no"]),
            status=str(row["status"]),
            change_summary=(str(row["change_summary"]) if row["change_summary"] else None),
            previous_revision_id=(str(row["previous_revision_id"]) if row["previous_revision_id"] else None),
            approval_request_id=(str(row["approval_request_id"]) if row["approval_request_id"] else None),
            approval_last_request_id=(str(row["approval_last_request_id"]) if row["approval_last_request_id"] else None),
            approval_round=int(row["approval_round"] or 0),
            approval_submitted_at_ms=(int(row["approval_submitted_at_ms"]) if row["approval_submitted_at_ms"] is not None else None),
            approval_completed_at_ms=(int(row["approval_completed_at_ms"]) if row["approval_completed_at_ms"] is not None else None),
            current_approval_step_no=(int(row["current_approval_step_no"]) if row["current_approval_step_no"] is not None else None),
            current_approval_step_name=(str(row["current_approval_step_name"]) if row["current_approval_step_name"] else None),
            current_approval_step_timeout_reminder_minutes=(
                int(row["current_approval_step_timeout_reminder_minutes"])
                if row["current_approval_step_timeout_reminder_minutes"] is not None
                else None
            ),
            current_approval_step_overdue_at_ms=(
                int(row["current_approval_step_overdue_at_ms"])
                if row["current_approval_step_overdue_at_ms"] is not None
                else None
            ),
            current_approval_step_last_reminded_at_ms=(
                int(row["current_approval_step_last_reminded_at_ms"])
                if row["current_approval_step_last_reminded_at_ms"] is not None
                else None
            ),
            release_mode=(str(row["release_mode"]) if row["release_mode"] else None),
            release_manual_archive_completed_by=(
                str(row["release_manual_archive_completed_by"]) if row["release_manual_archive_completed_by"] else None
            ),
            release_manual_archive_completed_at_ms=(
                int(row["release_manual_archive_completed_at_ms"])
                if row["release_manual_archive_completed_at_ms"] is not None
                else None
            ),
            approved_by=(str(row["approved_by"]) if row["approved_by"] else None),
            approved_at_ms=(int(row["approved_at_ms"]) if row["approved_at_ms"] is not None else None),
            effective_at_ms=(int(row["effective_at_ms"]) if row["effective_at_ms"] is not None else None),
            obsolete_at_ms=(int(row["obsolete_at_ms"]) if row["obsolete_at_ms"] is not None else None),
            obsolete_requested_by=(str(row["obsolete_requested_by"]) if row["obsolete_requested_by"] else None),
            obsolete_requested_at_ms=(int(row["obsolete_requested_at_ms"]) if row["obsolete_requested_at_ms"] is not None else None),
            obsolete_reason=(str(row["obsolete_reason"]) if row["obsolete_reason"] else None),
            obsolete_retention_until_ms=(
                int(row["obsolete_retention_until_ms"]) if row["obsolete_retention_until_ms"] is not None else None
            ),
            obsolete_approved_by=(str(row["obsolete_approved_by"]) if row["obsolete_approved_by"] else None),
            obsolete_approved_at_ms=(int(row["obsolete_approved_at_ms"]) if row["obsolete_approved_at_ms"] is not None else None),
            destruction_confirmed_by=(str(row["destruction_confirmed_by"]) if row["destruction_confirmed_by"] else None),
            destruction_confirmed_at_ms=(
                int(row["destruction_confirmed_at_ms"]) if row["destruction_confirmed_at_ms"] is not None else None
            ),
            destruction_notes=(str(row["destruction_notes"]) if row["destruction_notes"] else None),
            superseded_at_ms=(int(row["superseded_at_ms"]) if row["superseded_at_ms"] is not None else None),
            superseded_by_revision_id=(str(row["superseded_by_revision_id"]) if row["superseded_by_revision_id"] else None),
            created_by=str(row["created_by"]),
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            filename=str(row["filename"]),
            file_size=int(row["file_size"]),
            mime_type=str(row["mime_type"]),
            uploaded_by=str(row["uploaded_by"]),
            uploaded_at_ms=int(row["uploaded_at_ms"]),
            reviewed_by=(str(row["reviewed_by"]) if row["reviewed_by"] else None),
            reviewed_at_ms=(int(row["reviewed_at_ms"]) if row["reviewed_at_ms"] is not None else None),
            review_notes=(str(row["review_notes"]) if row["review_notes"] else None),
            ragflow_doc_id=(str(row["ragflow_doc_id"]) if row["ragflow_doc_id"] else None),
            kb_id=str(row["kb_id"]),
            kb_dataset_id=(str(row["kb_dataset_id"]) if row["kb_dataset_id"] else None),
            kb_name=(str(row["kb_name"]) if row["kb_name"] else None),
            file_sha256=(str(row["file_sha256"]) if row["file_sha256"] else None),
            file_path=str(row["file_path"]),
        )

    def _document_from_row(
        self,
        row,
        *,
        current_revision: ControlledRevision | None = None,
        effective_revision: ControlledRevision | None = None,
        revisions: list[ControlledRevision] | None = None,
    ) -> ControlledDocument:
        return ControlledDocument(
            controlled_document_id=str(row["controlled_document_id"]),
            doc_code=str(row["doc_code"]),
            title=str(row["title"]),
            document_type=str(row["document_type"]),
            product_name=(str(row["product_name"]) if row["product_name"] else None),
            registration_ref=(str(row["registration_ref"]) if row["registration_ref"] else None),
            target_kb_id=str(row["target_kb_id"]),
            target_kb_name=(str(row["target_kb_name"]) if row["target_kb_name"] else None),
            distribution_department_ids=self._parse_distribution_department_ids_json(row["distribution_department_ids_json"]),
            current_revision_id=(str(row["current_revision_id"]) if row["current_revision_id"] else None),
            effective_revision_id=(str(row["effective_revision_id"]) if row["effective_revision_id"] else None),
            created_by=str(row["created_by"]),
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            current_revision=current_revision,
            effective_revision=effective_revision,
            revisions=revisions,
        )

    def _get_revision_rows(self, conn, *, controlled_document_id: str) -> list:
        return conn.execute(
            """
            SELECT
                r.controlled_revision_id,
                r.controlled_document_id,
                r.kb_doc_id,
                r.revision_no,
                r.status,
                r.change_summary,
                r.previous_revision_id,
                r.approval_request_id,
                r.approval_last_request_id,
                r.approval_round,
                r.approval_submitted_at_ms,
                r.approval_completed_at_ms,
                r.current_approval_step_no,
                r.current_approval_step_name,
                r.current_approval_step_timeout_reminder_minutes,
                r.current_approval_step_overdue_at_ms,
                r.current_approval_step_last_reminded_at_ms,
                r.release_mode,
                r.release_manual_archive_completed_by,
                r.release_manual_archive_completed_at_ms,
                r.approved_by,
                r.approved_at_ms,
                r.effective_at_ms,
                r.obsolete_at_ms,
                r.obsolete_requested_by,
                r.obsolete_requested_at_ms,
                r.obsolete_reason,
                r.obsolete_retention_until_ms,
                r.obsolete_approved_by,
                r.obsolete_approved_at_ms,
                r.destruction_confirmed_by,
                r.destruction_confirmed_at_ms,
                r.destruction_notes,
                r.superseded_at_ms,
                r.superseded_by_revision_id,
                r.created_by,
                r.created_at_ms,
                r.updated_at_ms,
                k.filename,
                k.file_size,
                k.mime_type,
                k.uploaded_by,
                k.uploaded_at_ms,
                k.reviewed_by,
                k.reviewed_at_ms,
                k.review_notes,
                k.ragflow_doc_id,
                k.kb_id,
                k.kb_dataset_id,
                k.kb_name,
                k.file_sha256,
                k.file_path
            FROM controlled_revisions r
            JOIN kb_documents k
              ON k.doc_id = r.kb_doc_id
            WHERE r.controlled_document_id = ?
            ORDER BY r.revision_no DESC, r.created_at_ms DESC
            """,
            (controlled_document_id,),
        ).fetchall()

    def _load_document(self, conn, *, controlled_document_id: str) -> ControlledDocument:
        row = conn.execute(
            """
            SELECT
                controlled_document_id,
                doc_code,
                title,
                document_type,
                product_name,
                registration_ref,
                target_kb_id,
                target_kb_name,
                distribution_department_ids_json,
                current_revision_id,
                effective_revision_id,
                created_by,
                created_at_ms,
                updated_at_ms
            FROM controlled_documents
            WHERE controlled_document_id = ?
            """,
            (controlled_document_id,),
        ).fetchone()
        if row is None:
            raise DocumentControlError("controlled_document_not_found", status_code=404)
        revisions = [
            self._revision_from_joined_row(item)
            for item in self._get_revision_rows(conn, controlled_document_id=controlled_document_id)
        ]
        revisions_by_id = {item.controlled_revision_id: item for item in revisions}
        return self._document_from_row(
            row,
            current_revision=revisions_by_id.get(str(row["current_revision_id"])) if row["current_revision_id"] else None,
            effective_revision=revisions_by_id.get(str(row["effective_revision_id"])) if row["effective_revision_id"] else None,
            revisions=revisions,
        )

    def _load_revision(self, conn, *, controlled_revision_id: str) -> ControlledRevision:
        row = conn.execute(
            """
            SELECT
                r.controlled_revision_id,
                r.controlled_document_id,
                r.kb_doc_id,
                r.revision_no,
                r.status,
                r.change_summary,
                r.previous_revision_id,
                r.approval_request_id,
                r.approval_last_request_id,
                r.approval_round,
                r.approval_submitted_at_ms,
                r.approval_completed_at_ms,
                r.current_approval_step_no,
                r.current_approval_step_name,
                r.current_approval_step_timeout_reminder_minutes,
                r.current_approval_step_overdue_at_ms,
                r.current_approval_step_last_reminded_at_ms,
                r.release_mode,
                r.release_manual_archive_completed_by,
                r.release_manual_archive_completed_at_ms,
                r.approved_by,
                r.approved_at_ms,
                r.effective_at_ms,
                r.obsolete_at_ms,
                r.obsolete_requested_by,
                r.obsolete_requested_at_ms,
                r.obsolete_reason,
                r.obsolete_retention_until_ms,
                r.obsolete_approved_by,
                r.obsolete_approved_at_ms,
                r.destruction_confirmed_by,
                r.destruction_confirmed_at_ms,
                r.destruction_notes,
                r.superseded_at_ms,
                r.superseded_by_revision_id,
                r.created_by,
                r.created_at_ms,
                r.updated_at_ms,
                k.filename,
                k.file_size,
                k.mime_type,
                k.uploaded_by,
                k.uploaded_at_ms,
                k.reviewed_by,
                k.reviewed_at_ms,
                k.review_notes,
                k.ragflow_doc_id,
                k.kb_id,
                k.kb_dataset_id,
                k.kb_name,
                k.file_sha256,
                k.file_path
            FROM controlled_revisions r
            JOIN kb_documents k
              ON k.doc_id = r.kb_doc_id
            WHERE r.controlled_revision_id = ?
            """,
            (controlled_revision_id,),
        ).fetchone()
        if row is None:
            raise DocumentControlError("controlled_revision_not_found", status_code=404)
        return self._revision_from_joined_row(row)

    def list_documents(
        self,
        *,
        allowed_kb_refs: list[str] | None = None,
        doc_code: str | None = None,
        title: str | None = None,
        document_type: str | None = None,
        product_name: str | None = None,
        registration_ref: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ControlledDocument]:
        refs = [str(item).strip() for item in (allowed_kb_refs or []) if str(item).strip()]
        conn = self._connect()
        try:
            sql = """
                SELECT d.controlled_document_id
                FROM controlled_documents d
                LEFT JOIN controlled_revisions r
                  ON r.controlled_revision_id = d.current_revision_id
                WHERE 1 = 1
            """
            params: list[object] = []
            if refs:
                placeholders = ",".join("?" for _ in refs)
                sql += f" AND (d.target_kb_id IN ({placeholders}) OR d.target_kb_name IN ({placeholders}))"
                params.extend(refs)
                params.extend(refs)
            if doc_code:
                sql += " AND d.doc_code LIKE ?"
                params.append(f"%{str(doc_code).strip()}%")
            if title:
                sql += " AND d.title LIKE ?"
                params.append(f"%{str(title).strip()}%")
            if document_type:
                sql += " AND d.document_type = ?"
                params.append(str(document_type).strip())
            if product_name:
                sql += " AND IFNULL(d.product_name, '') LIKE ?"
                params.append(f"%{str(product_name).strip()}%")
            if registration_ref:
                sql += " AND IFNULL(d.registration_ref, '') LIKE ?"
                params.append(f"%{str(registration_ref).strip()}%")
            if status:
                sql += " AND IFNULL(r.status, '') = ?"
                params.append(str(status).strip())
            if query:
                sql += (
                    " AND (d.doc_code LIKE ? OR d.title LIKE ? OR IFNULL(d.product_name, '') LIKE ? "
                    "OR IFNULL(d.registration_ref, '') LIKE ?)"
                )
                pattern = f"%{str(query).strip()}%"
                params.extend([pattern, pattern, pattern, pattern])
            sql += " ORDER BY d.updated_at_ms DESC LIMIT ?"
            params.append(int(max(1, min(500, limit))))
            rows = conn.execute(sql, params).fetchall()
            return [self._load_document(conn, controlled_document_id=str(row["controlled_document_id"])) for row in rows]
        finally:
            conn.close()

    def get_document(self, *, controlled_document_id: str) -> ControlledDocument:
        conn = self._connect()
        try:
            return self._load_document(conn, controlled_document_id=controlled_document_id)
        finally:
            conn.close()

    def get_revision(self, *, controlled_revision_id: str) -> ControlledRevision:
        conn = self._connect()
        try:
            return self._load_revision(conn, controlled_revision_id=controlled_revision_id)
        finally:
            conn.close()

    def get_document_distribution_departments(self, *, controlled_document_id: str) -> list[int]:
        clean_document_id = self._require_text(controlled_document_id, "controlled_document_id_required")
        conn = self._connect()
        try:
            return self._load_distribution_department_ids(conn, controlled_document_id=clean_document_id)
        finally:
            conn.close()

    def set_document_distribution_departments(
        self,
        *,
        controlled_document_id: str,
        department_ids: list[object] | None,
        ctx,
    ) -> list[int]:
        clean_document_id = self._require_text(controlled_document_id, "controlled_document_id_required")
        normalized_department_ids = self._normalize_department_ids(department_ids)
        if not normalized_department_ids:
            raise DocumentControlError("document_control_distribution_departments_required", status_code=409)
        now_ms = self._now_ms()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._update_distribution_department_ids(
                conn,
                controlled_document_id=clean_document_id,
                department_ids=normalized_department_ids,
                now_ms=now_ms,
            )
            conn.commit()
        finally:
            conn.close()
        return normalized_department_ids

    def _insert_controlled_document(
        self,
        conn,
        *,
        controlled_document_id: str,
        doc_code: str,
        title: str,
        document_type: str,
        product_name: str | None,
        registration_ref: str | None,
        target_kb_id: str,
        target_kb_name: str | None,
        revision_id: str,
        created_by: str,
        now_ms: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO controlled_documents (
                controlled_document_id,
                doc_code,
                title,
                document_type,
                product_name,
                registration_ref,
                target_kb_id,
                target_kb_name,
                current_revision_id,
                effective_revision_id,
                created_by,
                created_at_ms,
                updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                controlled_document_id,
                doc_code,
                title,
                document_type,
                product_name,
                registration_ref,
                target_kb_id,
                target_kb_name,
                revision_id,
                None,
                created_by,
                now_ms,
                now_ms,
            ),
        )

    def _insert_controlled_revision(
        self,
        conn,
        *,
        revision_id: str,
        controlled_document_id: str,
        kb_doc_id: str,
        revision_no: int,
        change_summary: str | None,
        previous_revision_id: str | None,
        created_by: str,
        now_ms: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO controlled_revisions (
                controlled_revision_id,
                controlled_document_id,
                kb_doc_id,
                revision_no,
                status,
                change_summary,
                previous_revision_id,
                approval_request_id,
                approval_last_request_id,
                approval_round,
                approval_submitted_at_ms,
                approval_completed_at_ms,
                current_approval_step_no,
                current_approval_step_name,
                current_approval_step_timeout_reminder_minutes,
                current_approval_step_overdue_at_ms,
                current_approval_step_last_reminded_at_ms,
                release_mode,
                release_manual_archive_completed_by,
                release_manual_archive_completed_at_ms,
                approved_by,
                approved_at_ms,
                effective_at_ms,
                obsolete_at_ms,
                created_by,
                created_at_ms,
                updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?, ?)
            """,
            (
                revision_id,
                controlled_document_id,
                kb_doc_id,
                revision_no,
                REVISION_STATUS_DRAFT,
                change_summary,
                previous_revision_id,
                created_by,
                now_ms,
                now_ms,
            ),
        )

    def _cleanup_failed_create(self, *, kb_doc_id: str | None, file_path: Path | None) -> None:
        if kb_doc_id:
            try:
                self._deps.kb_store.delete_document(kb_doc_id)
            except Exception:
                pass
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass

    def create_document(
        self,
        *,
        doc_code: str,
        title: str,
        document_type: str,
        target_kb_id: str,
        created_by: str,
        upload_file,
        product_name: str | None = None,
        registration_ref: str | None = None,
        change_summary: str | None = None,
    ) -> ControlledDocument:
        clean_doc_code = self._require_text(doc_code, "doc_code_required")
        clean_title = self._require_text(title, "title_required")
        clean_type = self._require_text(document_type, "document_type_required")
        clean_target_kb = self._require_text(target_kb_id, "target_kb_id_required")
        clean_created_by = self._require_text(created_by, "created_by_required")
        clean_product_name = self._require_text(product_name, "product_name_required")
        clean_registration_ref = self._require_text(registration_ref, "registration_ref_required")
        controlled_document_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        now_ms = self._now_ms()
        file_path: Path | None = None
        kb_doc = None

        try:
            content = upload_file.file.read() if hasattr(upload_file, "file") else upload_file.read()
            filename = str(getattr(upload_file, "filename", "") or "").strip()
            display_name, file_path = self._staged_file_path(doc_code=clean_doc_code, revision_no=1, upload_filename=filename)
            mime_type = self._detect_mime(display_name, getattr(upload_file, "content_type", None))
            self._require_pdf_upload(filename=display_name, mime_type=mime_type)
            self._write_upload(path=file_path, content=content)
            kb_id, kb_dataset_id, kb_name = self._resolve_kb_info(clean_target_kb)
            kb_doc = self._create_kb_document(
                controlled_document_id=controlled_document_id,
                revision_no=1,
                file_path=file_path,
                filename=display_name,
                mime_type=mime_type,
                uploaded_by=clean_created_by,
                kb_id=kb_id,
                kb_dataset_id=kb_dataset_id,
                kb_name=kb_name,
                previous_doc_id=None,
                is_current=True,
            )

            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._insert_controlled_document(
                    conn,
                    controlled_document_id=controlled_document_id,
                    doc_code=clean_doc_code,
                    title=clean_title,
                    document_type=clean_type,
                    product_name=clean_product_name,
                    registration_ref=clean_registration_ref,
                    target_kb_id=kb_id,
                    target_kb_name=kb_name,
                    revision_id=revision_id,
                    created_by=clean_created_by,
                    now_ms=now_ms,
                )
                self._insert_controlled_revision(
                    conn,
                    revision_id=revision_id,
                    controlled_document_id=controlled_document_id,
                    kb_doc_id=kb_doc.doc_id,
                    revision_no=1,
                    change_summary=(str(change_summary).strip() if change_summary else None),
                    previous_revision_id=None,
                    created_by=clean_created_by,
                    now_ms=now_ms,
                )
                conn.commit()
            finally:
                conn.close()
            return self.get_document(controlled_document_id=controlled_document_id)
        except sqlite3.IntegrityError as exc:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise self._map_integrity_error(exc) from exc
        except Exception:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise

    def create_revision(
        self,
        *,
        controlled_document_id: str,
        created_by: str,
        upload_file,
        change_summary: str | None = None,
    ) -> ControlledDocument:
        clean_document_id = self._require_text(controlled_document_id, "controlled_document_id_required")
        clean_created_by = self._require_text(created_by, "created_by_required")

        conn = self._connect()
        try:
            document = self._load_document(conn, controlled_document_id=clean_document_id)
            current_revision = document.current_revision
            if current_revision is not None and current_revision.status != REVISION_STATUS_EFFECTIVE:
                raise DocumentControlError("current_revision_not_stable")
            next_revision_no = 1
            if document.revisions:
                next_revision_no = max(item.revision_no for item in document.revisions) + 1
            previous_revision_id = current_revision.controlled_revision_id if current_revision is not None else None
            previous_doc_id = current_revision.kb_doc_id if current_revision is not None else None
        finally:
            conn.close()

        revision_id = str(uuid.uuid4())
        now_ms = self._now_ms()
        file_path: Path | None = None
        kb_doc = None
        try:
            content = upload_file.file.read() if hasattr(upload_file, "file") else upload_file.read()
            filename = str(getattr(upload_file, "filename", "") or "").strip()
            display_name, file_path = self._staged_file_path(
                doc_code=document.doc_code,
                revision_no=next_revision_no,
                upload_filename=filename,
            )
            mime_type = self._detect_mime(display_name, getattr(upload_file, "content_type", None))
            self._require_pdf_upload(filename=display_name, mime_type=mime_type)
            self._write_upload(path=file_path, content=content)
            kb_id, kb_dataset_id, kb_name = self._resolve_kb_info(document.target_kb_id or (document.target_kb_name or ""))
            kb_doc = self._create_kb_document(
                controlled_document_id=clean_document_id,
                revision_no=next_revision_no,
                file_path=file_path,
                filename=display_name,
                mime_type=mime_type,
                uploaded_by=clean_created_by,
                kb_id=kb_id,
                kb_dataset_id=kb_dataset_id,
                kb_name=kb_name,
                previous_doc_id=previous_doc_id,
                is_current=False,
            )

            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._insert_controlled_revision(
                    conn,
                    revision_id=revision_id,
                    controlled_document_id=clean_document_id,
                    kb_doc_id=kb_doc.doc_id,
                    revision_no=next_revision_no,
                    change_summary=(str(change_summary).strip() if change_summary else None),
                    previous_revision_id=previous_revision_id,
                    created_by=clean_created_by,
                    now_ms=now_ms,
                )
                conn.execute(
                    """
                    UPDATE controlled_documents
                    SET current_revision_id = ?, updated_at_ms = ?
                    WHERE controlled_document_id = ?
                    """,
                    (revision_id, now_ms, clean_document_id),
                )
                conn.commit()
            finally:
                conn.close()
            return self.get_document(controlled_document_id=clean_document_id)
        except sqlite3.IntegrityError as exc:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise self._map_integrity_error(exc) from exc
        except Exception:
            self._cleanup_failed_create(kb_doc_id=(kb_doc.doc_id if kb_doc else None), file_path=file_path)
            raise

    def _emit_lifecycle_audit(
        self,
        *,
        ctx,
        revision: ControlledRevision,
        event_type: str,
        before: dict[str, object],
        after: dict[str, object],
        note: str | None,
    ) -> None:
        manager = getattr(self._deps, "audit_log_manager", None)
        if manager is not None:
            manager.safe_log_ctx_event(
                ctx=ctx,
                action="document_control_transition",
                source="document_control",
                resource_type="controlled_revision",
                resource_id=revision.controlled_revision_id,
                event_type=event_type,
                before=before,
                after=after,
                reason=note,
                doc_id=revision.kb_doc_id,
                filename=revision.filename,
                kb_id=(revision.kb_name or revision.kb_id),
                kb_dataset_id=revision.kb_dataset_id,
                kb_name=(revision.kb_name or revision.kb_id),
                meta={"controlled_document_id": revision.controlled_document_id, "revision_no": revision.revision_no},
            )
            return

        store = getattr(self._deps, "audit_log_store", None)
        if store is None:
            return
        store.log_event(
            action="document_control_transition",
            actor=ctx.payload.sub,
            source="document_control",
            resource_type="controlled_revision",
            resource_id=revision.controlled_revision_id,
            event_type=event_type,
            before=before,
            after=after,
            reason=note,
            doc_id=revision.kb_doc_id,
            filename=revision.filename,
            kb_id=(revision.kb_name or revision.kb_id),
            kb_dataset_id=revision.kb_dataset_id,
            kb_name=(revision.kb_name or revision.kb_id),
            meta={"controlled_document_id": revision.controlled_document_id, "revision_no": revision.revision_no},
            **actor_fields_from_ctx(self._deps, ctx),
        )

    def _load_revision_control_row(self, conn, *, controlled_revision_id: str):
        row = conn.execute(
            """
            SELECT
                controlled_revision_id,
                controlled_document_id,
                status,
                approval_request_id,
                approval_last_request_id,
                approval_round,
                approval_submitted_at_ms,
                approval_completed_at_ms,
                current_approval_step_no,
                current_approval_step_name,
                current_approval_step_timeout_reminder_minutes,
                current_approval_step_overdue_at_ms,
                current_approval_step_last_reminded_at_ms,
                approved_by,
                approved_at_ms,
                obsolete_requested_by,
                obsolete_requested_at_ms,
                obsolete_reason,
                obsolete_retention_until_ms,
                obsolete_approved_by,
                obsolete_approved_at_ms,
                destruction_confirmed_by,
                destruction_confirmed_at_ms,
                destruction_notes
            FROM controlled_revisions
            WHERE controlled_revision_id = ?
            """,
            (controlled_revision_id,),
        ).fetchone()
        if row is None:
            raise DocumentControlError("controlled_revision_not_found", status_code=404)
        return row

    def _require_user_store(self):
        operation_approval_service = getattr(self._deps, "operation_approval_service", None)
        operation_approval_user_store = getattr(operation_approval_service, "_user_store", None)
        if operation_approval_user_store is not None and callable(
            getattr(operation_approval_user_store, "get_by_user_id", None)
        ):
            return operation_approval_user_store

        user_store = getattr(self._deps, "user_store", None)
        if user_store is None or not callable(getattr(user_store, "get_by_user_id", None)):
            raise DocumentControlError("document_control_user_store_unavailable", status_code=500)
        return user_store

    def _resolve_active_user(self, *, user_id: str):
        store = self._require_user_store()
        user = store.get_by_user_id(user_id)
        if user is None:
            raise DocumentControlError("workflow_approver_not_found", status_code=409)
        if str(getattr(user, "status", "") or "").strip().lower() != "active":
            raise DocumentControlError("workflow_approver_inactive", status_code=409)
        return user

    def _normalize_workflow_steps(self, *, document_type: str) -> list[dict[str, object]]:
        workflow = self.get_document_type_workflow(document_type=document_type)
        raw_steps = workflow.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise DocumentControlError("document_control_workflow_not_configured", status_code=409)

        normalized: list[dict[str, object]] = []
        for index, raw_step in enumerate(raw_steps, start=1):
            if not isinstance(raw_step, dict):
                raise DocumentControlError("document_control_workflow_step_invalid", status_code=409)
            step_type = str(raw_step.get("step_type") or "").strip().lower()
            if step_type not in WORKFLOW_STEP_SEQUENCE:
                raise DocumentControlError("document_control_workflow_step_type_invalid", status_code=409)
            approval_rule = str(raw_step.get("approval_rule") or "").strip().lower()
            if approval_rule not in {"all", "any"}:
                raise DocumentControlError("document_control_workflow_approval_rule_invalid", status_code=409)
            member_source = str(raw_step.get("member_source") or "").strip()
            if not member_source:
                raise DocumentControlError("document_control_workflow_member_source_required", status_code=409)
            timeout_reminder_minutes = raw_step.get("timeout_reminder_minutes")
            try:
                timeout_reminder_minutes = int(timeout_reminder_minutes)
            except (TypeError, ValueError):
                raise DocumentControlError("document_control_workflow_timeout_invalid", status_code=409) from None
            if timeout_reminder_minutes <= 0:
                raise DocumentControlError("document_control_workflow_timeout_invalid", status_code=409)
            approver_user_ids = raw_step.get("approver_user_ids")
            if not isinstance(approver_user_ids, list) or not approver_user_ids:
                raise DocumentControlError("document_control_workflow_approvers_required", status_code=409)

            approvers: list[dict[str, str]] = []
            seen_user_ids: set[str] = set()
            for raw_user_id in approver_user_ids:
                user_id = str(raw_user_id or "").strip()
                if not user_id:
                    raise DocumentControlError("document_control_workflow_approver_invalid", status_code=409)
                if user_id in seen_user_ids:
                    raise DocumentControlError("document_control_workflow_approver_duplicated", status_code=409)
                user = self._resolve_active_user(user_id=user_id)
                approvers.append(
                    {
                        "user_id": user_id,
                        "username": str(getattr(user, "username", "") or "").strip() or user_id,
                    }
                )
                seen_user_ids.add(user_id)
            normalized.append(
                {
                    "step_no": index,
                    "step_name": step_type,
                    "step_type": step_type,
                    "approval_rule": approval_rule,
                    "member_source": member_source,
                    "timeout_reminder_minutes": timeout_reminder_minutes,
                    "approvers": approvers,
                }
            )

        if tuple(str(item["step_type"]) for item in normalized) != WORKFLOW_STEP_SEQUENCE:
            raise DocumentControlError("document_control_workflow_step_sequence_invalid", status_code=409)
        return normalized

    def _workflow_snapshot(self, *, steps: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "step_no": int(item["step_no"]),
                "step_name": str(item["step_name"]),
                "step_type": str(item["step_type"]),
                "approval_rule": str(item["approval_rule"]),
                "member_source": str(item["member_source"]),
                "timeout_reminder_minutes": int(item["timeout_reminder_minutes"]),
                "members": [
                    {
                        "member_type": "user",
                        "member_ref": str(approver["user_id"]),
                        "username": str(approver["username"]),
                    }
                    for approver in (item.get("approvers") or [])
                ],
            }
            for item in steps
        ]

    def _request_steps_from_workflow(self, *, steps: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "step_no": int(item["step_no"]),
                "step_name": str(item["step_name"]),
                "approval_rule": str(item["approval_rule"]),
                "timeout_reminder_minutes": int(item["timeout_reminder_minutes"]),
                "approvers": [
                    {
                        "user_id": str(approver["user_id"]),
                        "username": str(approver["username"]),
                    }
                    for approver in (item.get("approvers") or [])
                ],
            }
            for item in steps
        ]

    @staticmethod
    def _timeout_minutes_for_step(*, workflow_snapshot: dict[str, object] | None, step_no: int | None) -> int | None:
        if not isinstance(workflow_snapshot, dict):
            return None
        steps = workflow_snapshot.get("steps")
        if not isinstance(steps, list) or step_no is None:
            return None
        for item in steps:
            if not isinstance(item, dict):
                continue
            if int(item.get("step_no") or 0) != int(step_no):
                continue
            value = item.get("timeout_reminder_minutes")
            if value is None:
                return None
            return int(value)
        return None

    def _update_revision_approval_state(
        self,
        conn,
        *,
        controlled_revision_id: str,
        status: str,
        approval_request_id: str | None,
        approval_last_request_id: str | None,
        approval_round: int,
        approval_submitted_at_ms: int | None,
        approval_completed_at_ms: int | None,
        current_approval_step_no: int | None,
        current_approval_step_name: str | None,
        current_approval_step_timeout_reminder_minutes: int | None,
        current_approval_step_overdue_at_ms: int | None,
        current_approval_step_last_reminded_at_ms: int | None,
        release_mode: str | None,
        release_manual_archive_completed_by: str | None,
        release_manual_archive_completed_at_ms: int | None,
        approved_by: str | None,
        approved_at_ms: int | None,
        updated_at_ms: int,
    ) -> None:
        conn.execute(
            """
            UPDATE controlled_revisions
            SET
                status = ?,
                approval_request_id = ?,
                approval_last_request_id = ?,
                approval_round = ?,
                approval_submitted_at_ms = ?,
                approval_completed_at_ms = ?,
                current_approval_step_no = ?,
                current_approval_step_name = ?,
                current_approval_step_timeout_reminder_minutes = ?,
                current_approval_step_overdue_at_ms = ?,
                current_approval_step_last_reminded_at_ms = ?,
                release_mode = ?,
                release_manual_archive_completed_by = ?,
                release_manual_archive_completed_at_ms = ?,
                approved_by = ?,
                approved_at_ms = ?,
                updated_at_ms = ?
            WHERE controlled_revision_id = ?
            """,
            (
                status,
                approval_request_id,
                approval_last_request_id,
                approval_round,
                approval_submitted_at_ms,
                approval_completed_at_ms,
                current_approval_step_no,
                current_approval_step_name,
                current_approval_step_timeout_reminder_minutes,
                current_approval_step_overdue_at_ms,
                current_approval_step_last_reminded_at_ms,
                release_mode,
                release_manual_archive_completed_by,
                release_manual_archive_completed_at_ms,
                approved_by,
                approved_at_ms,
                updated_at_ms,
                controlled_revision_id,
            ),
        )

    @staticmethod
    def _ctx_actor_username(ctx) -> str:
        value = str(getattr(getattr(ctx, "user", None), "username", "") or "").strip()
        return value or str(getattr(getattr(ctx, "payload", None), "sub", "") or "")

    @staticmethod
    def _ctx_actor_company_id(ctx) -> int | None:
        raw = getattr(getattr(ctx, "user", None), "company_id", None)
        if raw is None or raw == "":
            return None
        return int(raw)

    @staticmethod
    def _ctx_actor_department_id(ctx) -> int | None:
        raw = getattr(getattr(ctx, "user", None), "department_id", None)
        if raw is None or raw == "":
            return None
        return int(raw)

    def submit_revision_for_approval(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        actor_username = self._ctx_actor_username(ctx)
        now_ms = self._now_ms()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            before = revision.as_dict()
            if revision.status not in {REVISION_STATUS_DRAFT, REVISION_STATUS_APPROVAL_REJECTED}:
                raise DocumentControlError("document_control_submit_invalid_status", status_code=409)
            if str(revision_row["approval_request_id"] or "").strip():
                raise DocumentControlError("document_control_approval_request_active", status_code=409)

            document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
            normalized_workflow_steps = self._normalize_workflow_steps(document_type=document.document_type)
            request_steps = self._request_steps_from_workflow(steps=normalized_workflow_steps)
            workflow_snapshot_steps = self._workflow_snapshot(steps=normalized_workflow_steps)
            request_id = str(uuid.uuid4())
            created_request = self._approval_store.create_request(
                request_id=request_id,
                operation_type=OPERATION_TYPE_DOCUMENT_CONTROL_REVISION_APPROVAL,
                workflow_name=f"document_control_{document.document_type}_approval",
                applicant_user_id=actor_user_id,
                applicant_username=actor_username,
                company_id=self._ctx_actor_company_id(ctx),
                department_id=self._ctx_actor_department_id(ctx),
                target_ref=revision.controlled_revision_id,
                target_label=f"{document.doc_code}-v{revision.revision_no:03d}",
                summary={
                    "controlled_document_id": revision.controlled_document_id,
                    "controlled_revision_id": revision.controlled_revision_id,
                    "doc_code": document.doc_code,
                    "document_type": document.document_type,
                    "revision_no": revision.revision_no,
                },
                payload={
                    "controlled_document_id": revision.controlled_document_id,
                    "controlled_revision_id": revision.controlled_revision_id,
                },
                workflow_snapshot={
                    "name": f"document_control_{document.document_type}_approval",
                    "steps": workflow_snapshot_steps,
                },
                steps=request_steps,
                artifacts=[],
                conn=conn,
            )

            self._update_revision_approval_state(
                conn,
                controlled_revision_id=clean_revision_id,
                status=REVISION_STATUS_APPROVAL_IN_PROGRESS,
                approval_request_id=request_id,
                approval_last_request_id=request_id,
                approval_round=int(revision_row["approval_round"] or 0) + 1,
                approval_submitted_at_ms=now_ms,
                approval_completed_at_ms=None,
                current_approval_step_no=created_request.get("current_step_no"),
                current_approval_step_name=created_request.get("current_step_name"),
                current_approval_step_timeout_reminder_minutes=int(normalized_workflow_steps[0]["timeout_reminder_minutes"]),
                current_approval_step_overdue_at_ms=None,
                current_approval_step_last_reminded_at_ms=None,
                release_mode=None,
                release_manual_archive_completed_by=None,
                release_manual_archive_completed_at_ms=None,
                approved_by=revision.approved_by,
                approved_at_ms=revision.approved_at_ms,
                updated_at_ms=now_ms,
            )
            conn.execute(
                """
                UPDATE controlled_documents
                SET updated_at_ms = ?
                WHERE controlled_document_id = ?
                """,
                (now_ms, revision.controlled_document_id),
            )
            conn.execute(
                """
                UPDATE kb_documents
                SET status = 'in_review',
                    reviewed_by = COALESCE(reviewed_by, ?),
                    reviewed_at_ms = COALESCE(reviewed_at_ms, ?),
                    review_notes = COALESCE(review_notes, ?),
                    effective_status = ?
                WHERE doc_id = ?
                """,
                (
                    actor_user_id,
                    now_ms,
                    note,
                    REVISION_STATUS_APPROVAL_IN_PROGRESS,
                    revision.kb_doc_id,
                ),
            )
            conn.commit()
            updated_revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            updated_document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        finally:
            conn.close()

        submit_event_type = (
            "controlled_revision_resubmitted"
            if revision.status == REVISION_STATUS_APPROVAL_REJECTED
            else "controlled_revision_submit"
        )
        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=updated_revision,
            event_type=submit_event_type,
            before=before,
            after=updated_revision.as_dict(),
            note=note,
        )
        if created_request.get("current_step_no") is not None:
            self._emit_lifecycle_audit(
                ctx=ctx,
                revision=updated_revision,
                event_type="controlled_revision_step_activated",
                before=updated_revision.as_dict(),
                after=updated_revision.as_dict(),
                note=(
                    f"step={created_request.get('current_step_name')}|"
                    f"step_no={created_request.get('current_step_no')}"
                ),
            )
        return updated_document

    def _require_active_approval_request(
        self,
        conn,
        *,
        revision: ControlledRevision,
        revision_row,
    ) -> tuple[str, dict]:
        if revision.status != REVISION_STATUS_APPROVAL_IN_PROGRESS:
            raise DocumentControlError("document_control_approval_not_in_progress", status_code=409)
        request_id = str(revision_row["approval_request_id"] or "").strip()
        if not request_id:
            raise DocumentControlError("document_control_approval_request_missing", status_code=409)
        request_data = self._approval_store.get_request(request_id, conn=conn)
        if request_data is None:
            raise DocumentControlError("document_control_approval_request_not_found", status_code=409)
        if str(request_data.get("status") or "") != REQUEST_STATUS_IN_APPROVAL:
            raise DocumentControlError("document_control_approval_request_not_active", status_code=409)
        return request_id, request_data

    def approve_revision_approval_step(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        actor_username = self._ctx_actor_username(ctx)
        now_ms = self._now_ms()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            before = revision.as_dict()
            request_id, request_data = self._require_active_approval_request(conn, revision=revision, revision_row=revision_row)
            if str(request_data.get("applicant_user_id") or "") == actor_user_id:
                raise DocumentControlError("document_control_approval_role_conflict", status_code=409)
            transition = self._approval_decision_service.approve_request_state(
                request_id=request_id,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                notes=note,
                signature_id=f"document_control:{uuid.uuid4()}",
                conn=conn,
            )

            request_record = transition.request_data.to_dict()
            request_status = str(request_record.get("status") or "")
            if request_status == REQUEST_STATUS_IN_APPROVAL:
                next_revision_status = REVISION_STATUS_APPROVAL_IN_PROGRESS
                next_request_id: str | None = request_id
                completion_at_ms: int | None = None
                next_timeout_minutes = self._timeout_minutes_for_step(
                    workflow_snapshot=request_record.get("workflow_snapshot"),
                    step_no=request_record.get("current_step_no"),
                )
                approved_by = revision.approved_by
                approved_at_ms = revision.approved_at_ms
            elif request_status == REQUEST_STATUS_APPROVED_PENDING_EXECUTION:
                next_revision_status = REVISION_STATUS_APPROVED_PENDING_EFFECTIVE
                next_request_id = None
                completion_at_ms = now_ms
                next_timeout_minutes = None
                approved_by = actor_user_id
                approved_at_ms = now_ms
            else:
                raise DocumentControlError("document_control_approval_request_status_invalid", status_code=409)

            self._update_revision_approval_state(
                conn,
                controlled_revision_id=clean_revision_id,
                status=next_revision_status,
                approval_request_id=next_request_id,
                approval_last_request_id=(str(revision_row["approval_last_request_id"] or "") or request_id),
                approval_round=int(revision_row["approval_round"] or 0),
                approval_submitted_at_ms=(
                    int(revision_row["approval_submitted_at_ms"])
                    if revision_row["approval_submitted_at_ms"] is not None
                    else None
                ),
                approval_completed_at_ms=completion_at_ms,
                current_approval_step_no=request_record.get("current_step_no"),
                current_approval_step_name=request_record.get("current_step_name"),
                current_approval_step_timeout_reminder_minutes=next_timeout_minutes,
                current_approval_step_overdue_at_ms=None,
                current_approval_step_last_reminded_at_ms=None,
                release_mode=revision.release_mode,
                release_manual_archive_completed_by=revision.release_manual_archive_completed_by,
                release_manual_archive_completed_at_ms=revision.release_manual_archive_completed_at_ms,
                approved_by=approved_by,
                approved_at_ms=approved_at_ms,
                updated_at_ms=now_ms,
            )
            conn.execute(
                """
                UPDATE controlled_documents
                SET updated_at_ms = ?
                WHERE controlled_document_id = ?
                """,
                (now_ms, revision.controlled_document_id),
            )
            if next_revision_status == REVISION_STATUS_APPROVED_PENDING_EFFECTIVE:
                conn.execute(
                    """
                    UPDATE kb_documents
                    SET status = 'approved',
                        reviewed_by = ?,
                        reviewed_at_ms = ?,
                        review_notes = COALESCE(?, review_notes),
                        effective_status = ?
                    WHERE doc_id = ?
                    """,
                    (
                        actor_user_id,
                        now_ms,
                        note,
                        REVISION_STATUS_APPROVED_PENDING_EFFECTIVE,
                        revision.kb_doc_id,
                    ),
                )
            conn.commit()
            updated_revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            updated_document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        finally:
            conn.close()

        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=updated_revision,
            event_type="controlled_revision_step_approved",
            before=before,
            after=updated_revision.as_dict(),
            note=note,
        )
        if transition.notify_step_started:
            self._emit_lifecycle_audit(
                ctx=ctx,
                revision=updated_revision,
                event_type="controlled_revision_step_activated",
                before=updated_revision.as_dict(),
                after=updated_revision.as_dict(),
                note=(
                    f"step={transition.request_data.current_step_name}|"
                    f"step_no={transition.request_data.current_step_no}"
                ),
            )
        return updated_document

    def reject_revision_approval_step(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        actor_username = self._ctx_actor_username(ctx)
        now_ms = self._now_ms()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            before = revision.as_dict()
            request_id, request_data = self._require_active_approval_request(conn, revision=revision, revision_row=revision_row)
            if str(request_data.get("applicant_user_id") or "") == actor_user_id:
                raise DocumentControlError("document_control_approval_role_conflict", status_code=409)

            rejected_request = self._approval_decision_service.reject_request_state(
                request_id=request_id,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                notes=note,
                signature_id=f"document_control:{uuid.uuid4()}",
                conn=conn,
            )
            request_record = rejected_request.to_dict()
            if str(request_record.get("status") or "") != REQUEST_STATUS_REJECTED:
                raise DocumentControlError("document_control_approval_request_status_invalid", status_code=409)

            self._update_revision_approval_state(
                conn,
                controlled_revision_id=clean_revision_id,
                status=REVISION_STATUS_APPROVAL_REJECTED,
                approval_request_id=None,
                approval_last_request_id=(str(revision_row["approval_last_request_id"] or "") or request_id),
                approval_round=int(revision_row["approval_round"] or 0),
                approval_submitted_at_ms=(
                    int(revision_row["approval_submitted_at_ms"])
                    if revision_row["approval_submitted_at_ms"] is not None
                    else None
                ),
                approval_completed_at_ms=now_ms,
                current_approval_step_no=request_record.get("current_step_no"),
                current_approval_step_name=request_record.get("current_step_name"),
                current_approval_step_timeout_reminder_minutes=None,
                current_approval_step_overdue_at_ms=None,
                current_approval_step_last_reminded_at_ms=None,
                release_mode=revision.release_mode,
                release_manual_archive_completed_by=revision.release_manual_archive_completed_by,
                release_manual_archive_completed_at_ms=revision.release_manual_archive_completed_at_ms,
                approved_by=revision.approved_by,
                approved_at_ms=revision.approved_at_ms,
                updated_at_ms=now_ms,
            )
            conn.execute(
                """
                UPDATE controlled_documents
                SET updated_at_ms = ?
                WHERE controlled_document_id = ?
                """,
                (now_ms, revision.controlled_document_id),
            )
            conn.execute(
                """
                UPDATE kb_documents
                SET status = 'rejected',
                    reviewed_by = COALESCE(reviewed_by, ?),
                    reviewed_at_ms = COALESCE(reviewed_at_ms, ?),
                    review_notes = COALESCE(?, review_notes),
                    effective_status = ?
                WHERE doc_id = ?
                """,
                (
                    actor_user_id,
                    now_ms,
                    note,
                    REVISION_STATUS_APPROVAL_REJECTED,
                    revision.kb_doc_id,
                ),
            )
            conn.commit()
            updated_revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            updated_document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        finally:
            conn.close()

        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=updated_revision,
            event_type="controlled_revision_step_rejected",
            before=before,
            after=updated_revision.as_dict(),
            note=note,
        )
        return updated_document

    def add_sign_revision_approval_step(
        self,
        *,
        controlled_revision_id: str,
        approver_user_id: str,
        ctx,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        clean_approver_user_id = self._require_text(approver_user_id, "approver_user_id_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        actor_username = self._ctx_actor_username(ctx)
        now_ms = self._now_ms()

        is_admin = bool(getattr(getattr(ctx, "snapshot", None), "is_admin", False)) or (
            str(getattr(getattr(ctx, "user", None), "role", "") or "").strip().lower() == "admin"
        )

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            before = revision.as_dict()
            request_id, _ = self._require_active_approval_request(conn, revision=revision, revision_row=revision_row)

            active_step = self._approval_store.get_active_step(request_id=request_id, conn=conn)
            if active_step is None:
                raise DocumentControlError("document_control_approval_active_step_missing", status_code=409)
            active_step_id = str(active_step.get("request_step_id") or "").strip()
            active_step_no = int(active_step.get("step_no") or 0)
            if not active_step_id or active_step_no <= 0:
                raise DocumentControlError("document_control_approval_active_step_missing", status_code=409)

            if not is_admin:
                actor_step = self._approval_store.get_step_approver(
                    request_id=request_id,
                    step_no=active_step_no,
                    approver_user_id=actor_user_id,
                    conn=conn,
                )
                if actor_step is None:
                    raise DocumentControlError("document_control_add_sign_forbidden", status_code=403)

            existing = self._approval_store.get_step_approver(
                request_id=request_id,
                step_no=active_step_no,
                approver_user_id=clean_approver_user_id,
                conn=conn,
            )
            if existing is not None:
                raise DocumentControlError("document_control_add_sign_duplicated", status_code=409)

            approver_user = self._resolve_active_user(user_id=clean_approver_user_id)
            approver_username = str(getattr(approver_user, "username", "") or "").strip() or clean_approver_user_id

            self._approval_store.add_step_approver(
                request_id=request_id,
                request_step_id=active_step_id,
                step_no=active_step_no,
                approver_user_id=clean_approver_user_id,
                approver_username=approver_username,
                conn=conn,
            )
            self._approval_store.add_event(
                request_id=request_id,
                event_type="step_approver_added",
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                step_no=active_step_no,
                payload={
                    "added_user_id": clean_approver_user_id,
                    "added_username": approver_username,
                    "notes": note,
                },
                conn=conn,
            )
            conn.execute(
                """
                UPDATE controlled_revisions
                SET updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (now_ms, clean_revision_id),
            )
            conn.execute(
                """
                UPDATE controlled_documents
                SET updated_at_ms = ?
                WHERE controlled_document_id = ?
                """,
                (now_ms, revision.controlled_document_id),
            )
            conn.commit()
            updated_revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            updated_document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        finally:
            conn.close()

        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=updated_revision,
            event_type="controlled_revision_add_sign",
            before=before,
            after=updated_revision.as_dict(),
            note=note,
        )
        return updated_document

    def remind_overdue_revision_approval_step(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        note: str | None = None,
    ) -> dict[str, object]:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        now_ms = self._now_ms()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            request_id, request_data = self._require_active_approval_request(conn, revision=revision, revision_row=revision_row)
            active_step = self._approval_store.get_active_step(request_id=request_id, conn=conn)
            if active_step is None:
                raise DocumentControlError("document_control_approval_active_step_missing", status_code=409)

            timeout_minutes = (
                int(revision.current_approval_step_timeout_reminder_minutes)
                if revision.current_approval_step_timeout_reminder_minutes is not None
                else self._timeout_minutes_for_step(
                    workflow_snapshot=request_data.get("workflow_snapshot"),
                    step_no=active_step.get("step_no"),
                )
            )
            if timeout_minutes is None or int(timeout_minutes) <= 0:
                raise DocumentControlError("document_control_workflow_timeout_invalid", status_code=409)
            activated_at_ms = active_step.get("activated_at_ms")
            if activated_at_ms is None:
                raise DocumentControlError("document_control_approval_active_step_missing", status_code=409)

            overdue_at_ms = int(activated_at_ms) + int(timeout_minutes) * 60 * 1000
            if now_ms < overdue_at_ms:
                conn.commit()
                return {
                    "count": 0,
                    "items": [],
                    "overdue": False,
                    "due_at_ms": overdue_at_ms,
                    "reminded_at_ms": now_ms,
                }

            last_reminded_at_ms = revision.current_approval_step_last_reminded_at_ms
            current_day = now_ms // 86_400_000
            if last_reminded_at_ms is not None and int(last_reminded_at_ms) // 86_400_000 == current_day:
                conn.execute(
                    """
                    UPDATE controlled_revisions
                    SET current_approval_step_overdue_at_ms = COALESCE(current_approval_step_overdue_at_ms, ?),
                        updated_at_ms = ?
                    WHERE controlled_revision_id = ?
                    """,
                    (overdue_at_ms, now_ms, clean_revision_id),
                )
                conn.commit()
                return {
                    "count": 0,
                    "items": [],
                    "overdue": True,
                    "due_at_ms": overdue_at_ms,
                    "reminded_at_ms": int(last_reminded_at_ms),
                }

            steps = request_data.get("steps") if isinstance(request_data, dict) else None
            current_step_no = int(active_step.get("step_no") or 0)
            current_step_name = str(active_step.get("step_name") or "").strip()
            pending_user_ids: list[str] = []
            if isinstance(steps, list):
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    if int(step.get("step_no") or 0) != current_step_no:
                        continue
                    for approver in (step.get("approvers") or []):
                        if not isinstance(approver, dict):
                            continue
                        if str(approver.get("status") or "") != "pending":
                            continue
                        user_id = str(approver.get("approver_user_id") or "").strip()
                        if user_id:
                            pending_user_ids.append(user_id)
                    break
            pending_user_ids = sorted(set(pending_user_ids))
            if not pending_user_ids:
                conn.execute(
                    """
                    UPDATE controlled_revisions
                    SET current_approval_step_overdue_at_ms = COALESCE(current_approval_step_overdue_at_ms, ?),
                        current_approval_step_last_reminded_at_ms = ?,
                        updated_at_ms = ?
                    WHERE controlled_revision_id = ?
                    """,
                    (overdue_at_ms, now_ms, now_ms, clean_revision_id),
                )
                conn.commit()
                return {
                    "count": 0,
                    "items": [],
                    "overdue": True,
                    "due_at_ms": overdue_at_ms,
                    "reminded_at_ms": now_ms,
                }

            conn.execute(
                """
                UPDATE controlled_revisions
                SET current_approval_step_overdue_at_ms = COALESCE(current_approval_step_overdue_at_ms, ?),
                    current_approval_step_last_reminded_at_ms = ?,
                    updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (overdue_at_ms, now_ms, now_ms, clean_revision_id),
            )
            conn.commit()
        finally:
            conn.close()

        notification_manager = self._require_notification_manager()
        payload = {
            "event_type": NOTIFICATION_EVENT_DOC_CTRL_APPROVAL_STEP_OVERDUE,
            "title": f"审批步骤超时提醒: {revision.filename}",
            "body": f"步骤 {current_step_name or current_step_no} 已超过提醒阈值，请尽快处理。",
            "link_path": "/quality-system/doc-control",
            "resource_type": "controlled_revision",
            "resource_id": revision.controlled_revision_id,
            "due_at_ms": overdue_at_ms,
            "meta": {
                "controlled_document_id": revision.controlled_document_id,
                "controlled_revision_id": revision.controlled_revision_id,
                "step_no": current_step_no,
                "step_name": current_step_name,
            },
        }
        dedupe_day = now_ms // 86_400_000
        try:
            jobs = notification_manager.notify_event(
                event_type=NOTIFICATION_EVENT_DOC_CTRL_APPROVAL_STEP_OVERDUE,
                payload=payload,
                recipients=[{"user_id": user_id} for user_id in pending_user_ids],
                dedupe_key=f"doc_ctrl_approval_step_overdue:{clean_revision_id}:{current_step_no}:{dedupe_day}",
                channel_types=["in_app"],
            )
            for job in jobs:
                job_id = int(job.get("job_id") or 0)
                if job_id > 0:
                    notification_manager.dispatch_job(job_id=job_id)
        except NotificationManagerError as exc:
            raise DocumentControlError(str(exc.code), status_code=exc.status_code) from exc
        except Exception as exc:  # noqa: BLE001
            raise DocumentControlError(f"document_control_approval_step_remind_failed:{exc}", status_code=500) from exc
        notification_manager.dispatch_pending(limit=200)

        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=revision,
            event_type="controlled_revision_step_remind_overdue",
            before=revision.as_dict(),
            after={**revision.as_dict(), "current_approval_step_overdue_at_ms": overdue_at_ms, "current_approval_step_last_reminded_at_ms": now_ms},
            note=note or f"step={current_step_name}|step_no={current_step_no}",
        )
        return {
            "count": len(pending_user_ids),
            "items": [{"user_id": user_id} for user_id in pending_user_ids],
            "overdue": True,
            "due_at_ms": overdue_at_ms,
            "reminded_at_ms": now_ms,
        }

    def _delete_ragflow_document(self, *, revision: ControlledRevision) -> None:
        ragflow_doc_id = str(revision.ragflow_doc_id or "").strip()
        if not ragflow_doc_id:
            return
        dataset_ref = revision.kb_dataset_id or revision.kb_id or (revision.kb_name or "")
        try:
            success = bool(self._deps.ragflow_service.delete_document(ragflow_doc_id, dataset_name=dataset_ref))
        except Exception as exc:
            raise DocumentControlError(f"ragflow_delete_failed:{exc}", status_code=500) from exc
        if not success:
            raise DocumentControlError("ragflow_delete_failed", status_code=500)

    def _finalize_kb_doc_for_effective(self, *, kb_doc) -> str | None:
        file_path = Path(str(getattr(kb_doc, "file_path", "") or ""))
        if not file_path.exists():
            raise DocumentControlError("local_file_missing", status_code=409)

        try:
            file_content = file_path.read_bytes()
        except Exception as exc:
            raise DocumentControlError(f"read_file_failed:{exc}", status_code=500) from exc

        try:
            ragflow_doc_id = self._deps.ragflow_service.upload_document_blob(
                file_filename=str(getattr(kb_doc, "filename", "") or file_path.name),
                file_content=file_content,
                kb_id=str(getattr(kb_doc, "kb_id", "") or ""),
            )
        except Exception as exc:
            raise DocumentControlError(f"ragflow_upload_failed:{exc}", status_code=500) from exc

        if not ragflow_doc_id:
            raise DocumentControlError("ragflow_upload_failed", status_code=500)

        dataset_ref = (
            str(getattr(kb_doc, "kb_dataset_id", "") or "").strip()
            or str(getattr(kb_doc, "kb_id", "") or "").strip()
            or str(getattr(kb_doc, "kb_name", "") or "").strip()
        )
        if ragflow_doc_id == "uploaded":
            return str(ragflow_doc_id)

        try:
            parsed = self._deps.ragflow_service.parse_document(
                dataset_ref=dataset_ref,
                document_id=str(ragflow_doc_id),
            )
        except Exception as exc:
            raise DocumentControlError(f"ragflow_parse_failed:{exc}", status_code=500) from exc
        if not parsed:
            raise DocumentControlError("ragflow_parse_failed", status_code=500)
        return str(ragflow_doc_id)

    def _make_revision_effective(
        self,
        *,
        conn,
        ctx,
        revision: ControlledRevision,
        release_mode: str,
        note: str | None,
        pending_audits: list[dict[str, object]],
    ) -> None:
        now_ms = self._now_ms()
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        actor_username = self._ctx_actor_username(ctx)
        document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        previous_effective = document.effective_revision
        kb_doc = self._deps.kb_store.get_document(revision.kb_doc_id)
        if kb_doc is None:
            raise DocumentControlError("kb_document_not_found", status_code=409)

        if not getattr(kb_doc, "ragflow_doc_id", None):
            try:
                ragflow_doc_id = self._finalize_kb_doc_for_effective(kb_doc=kb_doc)
            except Exception as exc:
                raise DocumentControlError(f"document_finalize_failed:{exc}", status_code=500) from exc
        else:
            ragflow_doc_id = getattr(kb_doc, "ragflow_doc_id", None)

        replaced_revision_id: str | None = None
        if previous_effective is not None and previous_effective.controlled_revision_id != revision.controlled_revision_id:
            replaced_revision_id = previous_effective.controlled_revision_id
            before_superseded = previous_effective.as_dict()
            self._delete_ragflow_document(revision=previous_effective)
            conn.execute(
                """
                UPDATE controlled_revisions
                SET status = ?,
                    superseded_at_ms = ?,
                    superseded_by_revision_id = ?,
                    updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (
                    REVISION_STATUS_SUPERSEDED,
                    now_ms,
                    revision.controlled_revision_id,
                    now_ms,
                    previous_effective.controlled_revision_id,
                ),
            )
            conn.execute(
                """
                UPDATE kb_documents
                SET status = ?,
                    reviewed_by = COALESCE(reviewed_by, ?),
                    reviewed_at_ms = COALESCE(reviewed_at_ms, ?),
                    review_notes = COALESCE(review_notes, ?),
                    ragflow_doc_id = NULL,
                    superseded_by_doc_id = ?,
                    is_current = 0,
                    effective_status = ?
                WHERE doc_id = ?
                """,
                (
                    REVISION_STATUS_SUPERSEDED,
                    ctx.payload.sub,
                    now_ms,
                    note,
                    revision.kb_doc_id,
                    REVISION_STATUS_SUPERSEDED,
                    previous_effective.kb_doc_id,
                ),
            )
            superseded_after = self._load_revision(conn, controlled_revision_id=previous_effective.controlled_revision_id)
            conn.execute(
                """
                INSERT INTO controlled_revision_release_ledger (
                    ledger_id,
                    controlled_document_id,
                    event_type,
                    release_mode,
                    subject_revision_id,
                    other_revision_id,
                    actor_user_id,
                    actor_username,
                    created_at_ms,
                    note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    revision.controlled_document_id,
                    REVISION_STATUS_SUPERSEDED,
                    release_mode,
                    previous_effective.controlled_revision_id,
                    revision.controlled_revision_id,
                    actor_user_id,
                    actor_username,
                    now_ms,
                    note,
                ),
            )
            pending_audits.append(
                {
                    "ctx": ctx,
                    "revision": superseded_after,
                    "event_type": "controlled_revision_superseded",
                    "before": before_superseded,
                    "after": superseded_after.as_dict(),
                    "note": note,
                }
            )

        conn.execute(
            """
            UPDATE controlled_revisions
            SET status = 'effective',
                approved_by = COALESCE(approved_by, ?),
                approved_at_ms = COALESCE(approved_at_ms, ?),
                effective_at_ms = ?,
                superseded_at_ms = NULL,
                superseded_by_revision_id = NULL,
                release_mode = ?,
                updated_at_ms = ?
            WHERE controlled_revision_id = ?
            """,
            (
                ctx.payload.sub,
                now_ms,
                now_ms,
                release_mode,
                now_ms,
                revision.controlled_revision_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO controlled_revision_release_ledger (
                ledger_id,
                controlled_document_id,
                event_type,
                release_mode,
                subject_revision_id,
                other_revision_id,
                actor_user_id,
                actor_username,
                created_at_ms,
                note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                revision.controlled_document_id,
                "published",
                release_mode,
                revision.controlled_revision_id,
                replaced_revision_id,
                actor_user_id,
                actor_username,
                now_ms,
                note,
            ),
        )
        conn.execute(
            """
            UPDATE controlled_documents
            SET current_revision_id = ?,
                effective_revision_id = ?,
                updated_at_ms = ?
            WHERE controlled_document_id = ?
            """,
            (
                revision.controlled_revision_id,
                revision.controlled_revision_id,
                now_ms,
                revision.controlled_document_id,
            ),
        )
        conn.execute(
            """
            UPDATE kb_documents
            SET status = 'effective',
                reviewed_by = COALESCE(reviewed_by, ?),
                reviewed_at_ms = COALESCE(reviewed_at_ms, ?),
                review_notes = COALESCE(review_notes, ?),
                ragflow_doc_id = ?,
                superseded_by_doc_id = NULL,
                is_current = 1,
                effective_status = 'effective'
            WHERE doc_id = ?
            """,
            (
                ctx.payload.sub,
                now_ms,
                note or f"controlled_revision_published:{revision.controlled_revision_id}",
                ragflow_doc_id,
                revision.kb_doc_id,
            ),
        )
        effective_after = self._load_revision(conn, controlled_revision_id=revision.controlled_revision_id)
        pending_audits.append(
            {
                "ctx": ctx,
                "revision": effective_after,
                "event_type": "controlled_revision_published",
                "before": revision.as_dict(),
                "after": effective_after.as_dict(),
                "note": note,
            }
        )

    def _create_department_acks(
        self,
        *,
        conn,
        revision: ControlledRevision,
        controlled_document_id: str,
        department_ids: list[int],
        due_at_ms: int,
        now_ms: int,
    ) -> None:
        for department_id in department_ids:
            conn.execute(
                """
                INSERT INTO document_control_department_acks (
                    ack_id,
                    controlled_revision_id,
                    controlled_document_id,
                    department_id,
                    status,
                    due_at_ms,
                    confirmed_by_user_id,
                    confirmed_at_ms,
                    overdue_at_ms,
                    last_reminded_at_ms,
                    notes,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    revision.controlled_revision_id,
                    controlled_document_id,
                    int(department_id),
                    DEPARTMENT_ACK_STATUS_PENDING,
                    int(due_at_ms),
                    now_ms,
                    now_ms,
                ),
            )

    def _notify_department_acks_required(
        self,
        *,
        document: ControlledDocument,
        effective_revision: ControlledRevision | None,
        recipients_by_department: dict[int, list[str]],
        ack_due_at_ms: int,
    ) -> None:
        notification_manager = self._require_notification_manager()
        revision_label = (
            f"{document.doc_code}-v{int(effective_revision.revision_no):03d}"
            if effective_revision is not None
            else str(document.doc_code)
        )
        for department_id, recipient_user_ids in recipients_by_department.items():
            payload = {
                "event_type": NOTIFICATION_EVENT_DOC_CTRL_DEPT_ACK_REQUIRED,
                "title": f"文控发布部门确认: {revision_label}",
                "body": "文件已发布，请相关部门确认接收/执行并完成确认。",
                "link_path": "/quality-system/doc-control",
                "resource_type": "controlled_revision",
                "resource_id": str(effective_revision.controlled_revision_id if effective_revision else ""),
                "due_at_ms": int(ack_due_at_ms),
                "meta": {
                    "controlled_document_id": str(document.controlled_document_id),
                    "controlled_revision_id": str(effective_revision.controlled_revision_id if effective_revision else ""),
                    "department_id": int(department_id),
                    "doc_code": str(document.doc_code),
                    "revision_no": (int(effective_revision.revision_no) if effective_revision else None),
                },
            }
            try:
                jobs = notification_manager.notify_event(
                    event_type=NOTIFICATION_EVENT_DOC_CTRL_DEPT_ACK_REQUIRED,
                    payload=payload,
                    recipients=[{"user_id": str(uid)} for uid in recipient_user_ids],
                    dedupe_key=f"doc_ctrl_dept_ack_required:{effective_revision.controlled_revision_id if effective_revision else ''}:{int(department_id)}",
                    channel_types=["in_app"],
                )
                for job in jobs:
                    job_id = int(job.get("job_id") or 0)
                    if job_id > 0:
                        notification_manager.dispatch_job(job_id=job_id)
            except NotificationManagerError as exc:
                raise DocumentControlError(str(exc.code), status_code=exc.status_code) from exc
            except Exception as exc:  # noqa: BLE001
                raise DocumentControlError(f"document_control_department_ack_notify_failed:{exc}", status_code=500) from exc
        notification_manager.dispatch_pending(limit=200)

    def _mark_revision_obsolete(
        self,
        *,
        conn,
        ctx,
        revision: ControlledRevision,
        note: str | None,
        pending_audits: list[dict[str, object]],
    ) -> None:
        now_ms = self._now_ms()
        before = revision.as_dict()
        self._delete_ragflow_document(revision=revision)
        conn.execute(
            """
            UPDATE controlled_revisions
            SET status = 'obsolete',
                obsolete_at_ms = ?,
                updated_at_ms = ?
            WHERE controlled_revision_id = ?
            """,
            (now_ms, now_ms, revision.controlled_revision_id),
        )
        conn.execute(
            """
            UPDATE controlled_documents
            SET effective_revision_id = NULL,
                updated_at_ms = ?
            WHERE controlled_document_id = ?
            """,
            (now_ms, revision.controlled_document_id),
        )
        conn.execute(
            """
            UPDATE kb_documents
            SET status = 'obsolete',
                reviewed_by = COALESCE(reviewed_by, ?),
                reviewed_at_ms = COALESCE(reviewed_at_ms, ?),
                review_notes = COALESCE(review_notes, ?),
                ragflow_doc_id = NULL,
                is_current = 0,
                effective_status = 'obsolete'
            WHERE doc_id = ?
            """,
            (
                ctx.payload.sub,
                now_ms,
                note,
                revision.kb_doc_id,
            ),
        )
        obsolete_after = self._load_revision(conn, controlled_revision_id=revision.controlled_revision_id)
        pending_audits.append(
            {
                "ctx": ctx,
                "revision": obsolete_after,
                "event_type": "controlled_revision_obsolete",
                "before": before,
                "after": obsolete_after.as_dict(),
                "note": note,
            }
        )

    def publish_revision(
        self,
        *,
        controlled_revision_id: str,
        release_mode: str,
        ctx,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        clean_release_mode = self._require_text(release_mode, "release_mode_required")
        if clean_release_mode not in ALLOWED_RELEASE_MODES:
            raise DocumentControlError("invalid_release_mode")

        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        revision_preview = self.get_revision(controlled_revision_id=clean_revision_id)
        if revision_preview.status != REVISION_STATUS_APPROVED_PENDING_EFFECTIVE:
            raise DocumentControlError("document_control_publish_invalid_status", status_code=409)
        training_service = getattr(self._deps, "training_compliance_service", None)
        if training_service is None:
            raise DocumentControlError("training_compliance_service_unavailable", status_code=500)
        try:
            gate = training_service.get_revision_training_gate(controlled_revision_id=clean_revision_id)
        except TrainingComplianceError as exc:
            raise DocumentControlError(str(exc.code), status_code=exc.status_code) from exc
        if not bool(gate.get("configured")):
            raise DocumentControlError("document_control_training_gate_not_configured", status_code=409)
        gate_status = str(gate.get("gate_status") or "").strip().lower()
        if bool(gate.get("training_required")) and bool(gate.get("blocking")):
            error_code = {
                "pending_assignment": "document_control_training_pending_assignment",
                "questions_open": "document_control_training_questions_open",
                "in_progress": "document_control_training_in_progress",
            }.get(gate_status, "document_control_training_gate_blocked")
            raise DocumentControlError(error_code, status_code=409)

        recipients_by_department: dict[int, list[str]] = {}
        ack_due_at_ms: int | None = None
        department_ids: list[int] = []
        pending_audits: list[dict[str, object]] = []

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)

            now_ms = self._now_ms()
            department_ids = self._load_distribution_department_ids(
                conn,
                controlled_document_id=revision.controlled_document_id,
            )
            if not department_ids:
                raise DocumentControlError("document_control_distribution_departments_missing", status_code=409)
            for department_id in department_ids:
                recipient_user_ids = self._list_active_user_ids_for_department(conn, department_id=int(department_id))
                if not recipient_user_ids:
                    raise DocumentControlError(
                        f"document_control_department_recipients_missing:{int(department_id)}",
                        status_code=409,
                    )
                recipients_by_department[int(department_id)] = recipient_user_ids
            ack_due_at_ms = now_ms + DEPARTMENT_ACK_DUE_DAYS_DEFAULT * 86400 * 1000

            self._make_revision_effective(
                conn=conn,
                ctx=ctx,
                revision=revision,
                release_mode=clean_release_mode,
                note=note,
                pending_audits=pending_audits,
            )
            if clean_release_mode == RELEASE_MODE_AUTOMATIC:
                self._create_department_acks(
                    conn=conn,
                    revision=revision,
                    controlled_document_id=revision.controlled_document_id,
                    department_ids=department_ids,
                    due_at_ms=int(ack_due_at_ms),
                    now_ms=now_ms,
                )
                conn.execute(
                    """
                    UPDATE controlled_revisions
                    SET release_manual_archive_completed_by = ?,
                        release_manual_archive_completed_at_ms = ?,
                        updated_at_ms = ?
                    WHERE controlled_revision_id = ?
                    """,
                    (actor_user_id, now_ms, now_ms, revision.controlled_revision_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE controlled_revisions
                    SET release_manual_archive_completed_by = NULL,
                        release_manual_archive_completed_at_ms = NULL,
                        updated_at_ms = ?
                    WHERE controlled_revision_id = ?
                    """,
                    (now_ms, revision.controlled_revision_id),
                )
            conn.commit()
            document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
        finally:
            conn.close()

        for event in pending_audits:
            self._emit_lifecycle_audit(**event)

        if clean_release_mode == RELEASE_MODE_AUTOMATIC and ack_due_at_ms is not None:
            effective_revision = document.effective_revision or document.current_revision
            self._notify_department_acks_required(
                document=document,
                effective_revision=effective_revision,
                recipients_by_department=recipients_by_department,
                ack_due_at_ms=int(ack_due_at_ms),
            )
        return document

    def complete_manual_release_archive(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        now_ms = self._now_ms()
        recipients_by_department: dict[int, list[str]] = {}
        ack_due_at_ms: int | None = None

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            if revision.status != REVISION_STATUS_EFFECTIVE:
                raise DocumentControlError("document_control_manual_release_invalid_status", status_code=409)
            if revision.release_mode != RELEASE_MODE_MANUAL_BY_DOC_CONTROL:
                raise DocumentControlError("document_control_manual_release_not_required", status_code=409)
            if revision.release_manual_archive_completed_at_ms is not None:
                raise DocumentControlError("document_control_manual_release_already_completed", status_code=409)

            department_ids = self._load_distribution_department_ids(conn, controlled_document_id=revision.controlled_document_id)
            if not department_ids:
                raise DocumentControlError("document_control_distribution_departments_missing", status_code=409)
            for department_id in department_ids:
                recipient_user_ids = self._list_active_user_ids_for_department(conn, department_id=int(department_id))
                if not recipient_user_ids:
                    raise DocumentControlError(
                        f"document_control_department_recipients_missing:{int(department_id)}",
                        status_code=409,
                    )
                recipients_by_department[int(department_id)] = recipient_user_ids
            ack_due_at_ms = now_ms + DEPARTMENT_ACK_DUE_DAYS_DEFAULT * 86400 * 1000

            self._create_department_acks(
                conn=conn,
                revision=revision,
                controlled_document_id=revision.controlled_document_id,
                department_ids=department_ids,
                due_at_ms=int(ack_due_at_ms),
                now_ms=now_ms,
            )
            conn.execute(
                """
                UPDATE controlled_revisions
                SET release_manual_archive_completed_by = ?,
                    release_manual_archive_completed_at_ms = ?,
                    updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (actor_user_id, now_ms, now_ms, clean_revision_id),
            )
            conn.execute(
                """
                INSERT INTO controlled_revision_release_ledger (
                    ledger_id,
                    controlled_document_id,
                    event_type,
                    release_mode,
                    subject_revision_id,
                    other_revision_id,
                    actor_user_id,
                    actor_username,
                    created_at_ms,
                    note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    revision.controlled_document_id,
                    "manual_archive_completed",
                    RELEASE_MODE_MANUAL_BY_DOC_CONTROL,
                    revision.controlled_revision_id,
                    None,
                    actor_user_id,
                    self._ctx_actor_username(ctx),
                    now_ms,
                    note,
                ),
            )
            conn.commit()
            document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
            effective_revision = document.effective_revision or document.current_revision
        finally:
            conn.close()

        if ack_due_at_ms is not None:
            self._notify_department_acks_required(
                document=document,
                effective_revision=effective_revision,
                recipients_by_department=recipients_by_department,
                ack_due_at_ms=int(ack_due_at_ms),
            )
        return document

    def list_revision_department_acks(self, *, controlled_revision_id: str) -> list[dict[str, object]]:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT
                    ack_id,
                    controlled_revision_id,
                    controlled_document_id,
                    department_id,
                    status,
                    due_at_ms,
                    confirmed_by_user_id,
                    confirmed_at_ms,
                    overdue_at_ms,
                    last_reminded_at_ms,
                    notes,
                    created_at_ms,
                    updated_at_ms
                FROM document_control_department_acks
                WHERE controlled_revision_id = ?
                ORDER BY department_id ASC
                """,
                (clean_revision_id,),
            ).fetchall()
            items: list[dict[str, object]] = []
            for row in rows:
                items.append(
                    {
                        "ack_id": str(row["ack_id"]),
                        "controlled_revision_id": str(row["controlled_revision_id"]),
                        "controlled_document_id": str(row["controlled_document_id"]),
                        "department_id": int(row["department_id"] or 0),
                        "status": str(row["status"] or ""),
                        "due_at_ms": int(row["due_at_ms"] or 0),
                        "confirmed_by_user_id": (str(row["confirmed_by_user_id"]) if row["confirmed_by_user_id"] else None),
                        "confirmed_at_ms": (int(row["confirmed_at_ms"]) if row["confirmed_at_ms"] is not None else None),
                        "overdue_at_ms": (int(row["overdue_at_ms"]) if row["overdue_at_ms"] is not None else None),
                        "last_reminded_at_ms": (
                            int(row["last_reminded_at_ms"]) if row["last_reminded_at_ms"] is not None else None
                        ),
                        "notes": (str(row["notes"]) if row["notes"] is not None and str(row["notes"]).strip() else None),
                        "created_at_ms": int(row["created_at_ms"] or 0),
                        "updated_at_ms": int(row["updated_at_ms"] or 0),
                    }
                )
            return items
        finally:
            conn.close()

    def confirm_revision_department_ack(
        self,
        *,
        controlled_revision_id: str,
        department_id: int,
        ctx,
        notes: str | None = None,
    ) -> dict[str, object]:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        try:
            clean_department_id = int(department_id)
        except Exception as exc:  # noqa: BLE001
            raise DocumentControlError("invalid_department_id") from exc
        if clean_department_id <= 0:
            raise DocumentControlError("invalid_department_id")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        notes_clean = str(notes or "").strip() or None
        actor_department_id = getattr(getattr(ctx, "user", None), "department_id", None)
        if not bool(getattr(getattr(ctx, "snapshot", None), "is_admin", False)):
            if actor_department_id is None or str(actor_department_id).strip() == "":
                raise DocumentControlError("document_control_department_ack_forbidden", status_code=403)
            if int(actor_department_id) != clean_department_id:
                raise DocumentControlError("document_control_department_ack_forbidden", status_code=403)

        now_ms = self._now_ms()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT ack_id
                FROM document_control_department_acks
                WHERE controlled_revision_id = ? AND department_id = ?
                """,
                (clean_revision_id, clean_department_id),
            ).fetchone()
            if row is None:
                raise DocumentControlError("document_control_department_ack_not_found", status_code=404)
            ack_id = str(row["ack_id"])
            conn.execute(
                """
                UPDATE document_control_department_acks
                SET status = ?,
                    confirmed_by_user_id = ?,
                    confirmed_at_ms = ?,
                    notes = ?,
                    updated_at_ms = ?
                WHERE ack_id = ?
                """,
                (
                    DEPARTMENT_ACK_STATUS_CONFIRMED,
                    actor_user_id,
                    now_ms,
                    notes_clean,
                    now_ms,
                    ack_id,
                ),
            )
            conn.commit()
            updated = conn.execute(
                """
                SELECT
                    ack_id,
                    controlled_revision_id,
                    controlled_document_id,
                    department_id,
                    status,
                    due_at_ms,
                    confirmed_by_user_id,
                    confirmed_at_ms,
                    overdue_at_ms,
                    last_reminded_at_ms,
                    notes,
                    created_at_ms,
                    updated_at_ms
                FROM document_control_department_acks
                WHERE ack_id = ?
                """,
                (ack_id,),
            ).fetchone()
        finally:
            conn.close()

        ack: dict[str, object] = {
            "ack_id": str(updated["ack_id"]),
            "controlled_revision_id": str(updated["controlled_revision_id"]),
            "controlled_document_id": str(updated["controlled_document_id"]),
            "department_id": int(updated["department_id"] or 0),
            "status": str(updated["status"] or ""),
            "due_at_ms": int(updated["due_at_ms"] or 0),
            "confirmed_by_user_id": (str(updated["confirmed_by_user_id"]) if updated["confirmed_by_user_id"] else None),
            "confirmed_at_ms": (int(updated["confirmed_at_ms"]) if updated["confirmed_at_ms"] is not None else None),
            "overdue_at_ms": (int(updated["overdue_at_ms"]) if updated["overdue_at_ms"] is not None else None),
            "last_reminded_at_ms": (
                int(updated["last_reminded_at_ms"]) if updated["last_reminded_at_ms"] is not None else None
            ),
            "notes": (str(updated["notes"]) if updated["notes"] is not None and str(updated["notes"]).strip() else None),
            "created_at_ms": int(updated["created_at_ms"] or 0),
            "updated_at_ms": int(updated["updated_at_ms"] or 0),
        }
        store = getattr(self._deps, "audit_log_store", None)
        if store is not None:
            store.log_event(
                action="document_control_department_ack_confirm",
                actor=actor_user_id,
                source="document_control",
                resource_type="document_control_department_ack",
                resource_id=str(ack_id),
                event_type="confirmed",
                before=None,
                after=dict(ack),
                reason=notes_clean,
                meta={
                    "controlled_revision_id": clean_revision_id,
                    "department_id": clean_department_id,
                },
                **actor_fields_from_ctx(self._deps, ctx),
            )
        return ack

    def remind_overdue_revision_department_acks(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        note: str | None = None,
    ) -> dict[str, object]:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        now_ms = self._now_ms()

        target_ack_ids: list[str] = []
        recipients_by_department: dict[int, list[str]] = {}
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            if revision.status != REVISION_STATUS_EFFECTIVE:
                raise DocumentControlError("document_control_department_ack_remind_invalid_status", status_code=409)

            rows = conn.execute(
                """
                SELECT ack_id, department_id, status, due_at_ms
                FROM document_control_department_acks
                WHERE controlled_revision_id = ?
                  AND status != ?
                  AND due_at_ms <= ?
                ORDER BY department_id ASC
                """,
                (clean_revision_id, DEPARTMENT_ACK_STATUS_CONFIRMED, now_ms),
            ).fetchall()
            for row in rows:
                ack_id = str(row["ack_id"])
                department_id = int(row["department_id"] or 0)
                if department_id <= 0:
                    continue
                target_ack_ids.append(ack_id)
                if department_id not in recipients_by_department:
                    recipient_user_ids = self._list_active_user_ids_for_department(conn, department_id=department_id)
                    if not recipient_user_ids:
                        raise DocumentControlError(
                            f"document_control_department_recipients_missing:{department_id}",
                            status_code=409,
                        )
                    recipients_by_department[department_id] = recipient_user_ids

            for ack_id in target_ack_ids:
                conn.execute(
                    """
                    UPDATE document_control_department_acks
                    SET status = CASE
                        WHEN status = ? THEN ?
                        ELSE status
                    END,
                        overdue_at_ms = COALESCE(overdue_at_ms, ?),
                        updated_at_ms = ?
                    WHERE ack_id = ?
                    """,
                    (
                        DEPARTMENT_ACK_STATUS_PENDING,
                        DEPARTMENT_ACK_STATUS_OVERDUE,
                        now_ms,
                        now_ms,
                        ack_id,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        if not target_ack_ids:
            return {"count": 0, "items": [], "reminded_at_ms": now_ms}

        notification_manager = self._require_notification_manager()
        dedupe_day = int(now_ms / (86400 * 1000))
        for department_id, recipient_user_ids in recipients_by_department.items():
            payload = {
                "event_type": NOTIFICATION_EVENT_DOC_CTRL_DEPT_ACK_OVERDUE,
                "title": "文控发布确认逾期提醒",
                "body": "部门确认已逾期，请尽快完成确认。",
                "recipient_user_ids": list(recipient_user_ids),
                "link_path": "/quality-system/doc-control",
                "resource_type": "controlled_revision",
                "resource_id": clean_revision_id,
                "meta": {
                    "controlled_revision_id": clean_revision_id,
                    "department_id": int(department_id),
                },
            }
            try:
                jobs = notification_manager.notify_event(
                    event_type=NOTIFICATION_EVENT_DOC_CTRL_DEPT_ACK_OVERDUE,
                    payload=payload,
                    recipients=[{"user_id": str(uid)} for uid in recipient_user_ids],
                    dedupe_key=f"doc_ctrl_dept_ack_overdue:{clean_revision_id}:{int(department_id)}:{dedupe_day}",
                    channel_types=["in_app"],
                )
                for job in jobs:
                    job_id = int(job.get("job_id") or 0)
                    if job_id > 0:
                        notification_manager.dispatch_job(job_id=job_id)
            except NotificationManagerError as exc:
                raise DocumentControlError(str(exc.code), status_code=exc.status_code) from exc
            except Exception as exc:  # noqa: BLE001
                raise DocumentControlError(f"document_control_department_ack_remind_failed:{exc}", status_code=500) from exc

        notification_manager.dispatch_pending(limit=200)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for ack_id in target_ack_ids:
                conn.execute(
                    """
                    UPDATE document_control_department_acks
                    SET last_reminded_at_ms = ?,
                        updated_at_ms = ?
                    WHERE ack_id = ?
                    """,
                    (now_ms, now_ms, ack_id),
                )
            conn.commit()
        finally:
            conn.close()

        store = getattr(self._deps, "audit_log_store", None)
        if store is not None:
            store.log_event(
                action="document_control_department_ack_remind_overdue",
                actor=actor_user_id,
                source="document_control",
                resource_type="controlled_revision",
                resource_id=clean_revision_id,
                event_type="remind_overdue",
                before=None,
                after={"ack_ids": list(target_ack_ids), "department_ids": sorted(recipients_by_department.keys())},
                reason=str(note or "").strip() or None,
                meta={"count": len(target_ack_ids)},
                **actor_fields_from_ctx(self._deps, ctx),
            )

        return {
            "count": len(target_ack_ids),
            "items": [{"ack_id": ack_id} for ack_id in target_ack_ids],
            "reminded_at_ms": now_ms,
        }

    def make_revision_effective(
        self,
        *,
        controlled_revision_id: str,  # noqa: ARG002
        ctx,  # noqa: ARG002
        note: str | None = None,  # noqa: ARG002
    ) -> ControlledDocument:
        raise DocumentControlError("document_control_effective_removed_use_publish", status_code=410)

    def initiate_revision_obsolete(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        retirement_reason: str,
        retention_until_ms: int,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        clean_reason = self._require_text(retirement_reason, "retirement_reason_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        now_ms = self._now_ms()
        try:
            retention_until_ms = int(retention_until_ms)
        except Exception as exc:
            raise DocumentControlError("invalid_retention_until_ms") from exc
        if retention_until_ms <= now_ms:
            raise DocumentControlError("retention_until_must_be_future", status_code=409)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            if revision.status != REVISION_STATUS_EFFECTIVE:
                raise DocumentControlError("document_control_obsolete_invalid_status", status_code=409)
            if revision_row["obsolete_requested_at_ms"] is not None and revision_row["obsolete_approved_at_ms"] is None:
                raise DocumentControlError("document_control_obsolete_request_active", status_code=409)

            before = revision.as_dict()
            conn.execute(
                """
                UPDATE controlled_revisions
                SET obsolete_requested_by = ?,
                    obsolete_requested_at_ms = ?,
                    obsolete_reason = ?,
                    obsolete_retention_until_ms = ?,
                    obsolete_approved_by = NULL,
                    obsolete_approved_at_ms = NULL,
                    destruction_confirmed_by = NULL,
                    destruction_confirmed_at_ms = NULL,
                    destruction_notes = NULL,
                    updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (
                    actor_user_id,
                    now_ms,
                    clean_reason,
                    retention_until_ms,
                    now_ms,
                    clean_revision_id,
                ),
            )
            conn.execute(
                """
                UPDATE controlled_documents
                SET updated_at_ms = ?
                WHERE controlled_document_id = ?
                """,
                (now_ms, revision.controlled_document_id),
            )
            conn.commit()
            document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
            after_revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
        finally:
            conn.close()

        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=after_revision,
            event_type="controlled_revision_obsolete_initiated",
            before=before,
            after=after_revision.as_dict(),
            note=note or f"reason={clean_reason}|retention_until_ms={retention_until_ms}",
        )
        return document

    def approve_revision_obsolete(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        note: str | None = None,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        actor_username = self._ctx_actor_username(ctx)
        now_ms = self._now_ms()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            if revision.status != REVISION_STATUS_EFFECTIVE:
                raise DocumentControlError("document_control_obsolete_invalid_status", status_code=409)
            if revision_row["obsolete_requested_at_ms"] is None or revision_row["obsolete_approved_at_ms"] is not None:
                raise DocumentControlError("document_control_obsolete_request_missing", status_code=409)
            requested_by = str(revision_row["obsolete_requested_by"] or "").strip()
            if requested_by and requested_by == actor_user_id:
                raise DocumentControlError("document_control_obsolete_role_conflict", status_code=409)
            try:
                retention_until_ms = int(revision_row["obsolete_retention_until_ms"])
            except Exception as exc:
                raise DocumentControlError("invalid_retention_until_ms") from exc
            if retention_until_ms <= now_ms:
                raise DocumentControlError("retention_until_must_be_future", status_code=409)

            before = revision.as_dict()

            # Remove from ragflow index first, then retire to an immutable archive package.
            self._delete_ragflow_document(revision=revision)
            retired = RetiredRecordsService(kb_store=self._deps.kb_store).retire_document(
                doc_id=revision.kb_doc_id,
                retired_by=actor_user_id,
                retired_by_username=actor_username,
                retirement_reason=str(revision_row["obsolete_reason"] or "").strip() or "document_control_obsolete",
                retention_until_ms=retention_until_ms,
                archived_at_ms=now_ms,
                conn=conn,
            )

            conn.execute(
                """
                UPDATE controlled_revisions
                SET status = 'obsolete',
                    obsolete_at_ms = ?,
                    obsolete_approved_by = ?,
                    obsolete_approved_at_ms = ?,
                    updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (now_ms, actor_user_id, now_ms, now_ms, clean_revision_id),
            )
            conn.execute(
                """
                UPDATE controlled_documents
                SET effective_revision_id = NULL,
                    updated_at_ms = ?
                WHERE controlled_document_id = ?
                  AND effective_revision_id = ?
                """,
                (now_ms, revision.controlled_document_id, revision.controlled_revision_id),
            )
            conn.execute(
                """
                UPDATE kb_documents
                SET status = 'obsolete',
                    reviewed_by = COALESCE(reviewed_by, ?),
                    reviewed_at_ms = COALESCE(reviewed_at_ms, ?),
                    review_notes = COALESCE(?, review_notes),
                    ragflow_doc_id = NULL,
                    is_current = 0
                WHERE doc_id = ?
                """,
                (
                    actor_user_id,
                    now_ms,
                    note,
                    retired.doc_id,
                ),
            )
            conn.commit()
            document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
            after_revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
        finally:
            conn.close()

        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=after_revision,
            event_type="controlled_revision_obsolete",
            before=before,
            after=after_revision.as_dict(),
            note=note,
        )
        return document

    def confirm_revision_destruction(
        self,
        *,
        controlled_revision_id: str,
        ctx,
        destruction_notes: str,
    ) -> ControlledDocument:
        clean_revision_id = self._require_text(controlled_revision_id, "controlled_revision_id_required")
        clean_notes = self._require_text(destruction_notes, "destruction_notes_required")
        actor_user_id = self._require_text(str(getattr(ctx.payload, "sub", "") or ""), "actor_user_id_required")
        now_ms = self._now_ms()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
            revision_row = self._load_revision_control_row(conn, controlled_revision_id=clean_revision_id)
            if revision.status != REVISION_STATUS_OBSOLETE:
                raise DocumentControlError("document_control_destruction_invalid_status", status_code=409)

            kb_doc = self._deps.kb_store.get_document(revision.kb_doc_id)
            if kb_doc is None:
                raise DocumentControlError("kb_document_not_found", status_code=409)
            if str(getattr(kb_doc, "effective_status", "") or "").strip().lower() != "archived":
                raise DocumentControlError("document_not_retired", status_code=409)
            retention_until_ms = getattr(kb_doc, "retention_until_ms", None)
            if retention_until_ms is None:
                raise DocumentControlError("retention_until_missing", status_code=409)
            if int(retention_until_ms) >= now_ms:
                raise DocumentControlError("document_retention_not_expired", status_code=409)

            before = revision.as_dict()
            conn.execute(
                """
                UPDATE controlled_revisions
                SET destruction_confirmed_by = ?,
                    destruction_confirmed_at_ms = ?,
                    destruction_notes = ?,
                    updated_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (actor_user_id, now_ms, clean_notes, now_ms, clean_revision_id),
            )
            conn.commit()
            document = self._load_document(conn, controlled_document_id=revision.controlled_document_id)
            after_revision = self._load_revision(conn, controlled_revision_id=clean_revision_id)
        finally:
            conn.close()

        self._emit_lifecycle_audit(
            ctx=ctx,
            revision=after_revision,
            event_type="controlled_revision_destruction_confirmed",
            before=before,
            after=after_revision.as_dict(),
            note=clean_notes,
        )
        return document
