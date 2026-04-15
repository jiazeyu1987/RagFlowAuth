from __future__ import annotations

from typing import Any, TypeVar

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .repositories import (
    OperationApprovalArtifactRepository,
    OperationApprovalEventRepository,
    OperationApprovalMigrationRepository,
    OperationApprovalRequestRepository,
    OperationApprovalStepRepository,
    OperationApprovalWorkflowRepository,
)


T = TypeVar("T")


class OperationApprovalStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._workflow_repo = OperationApprovalWorkflowRepository(connection_factory=self._conn)
        self._request_repo = OperationApprovalRequestRepository(connection_factory=self._conn)
        self._step_repo = OperationApprovalStepRepository(connection_factory=self._conn)
        self._event_repo = OperationApprovalEventRepository(connection_factory=self._conn)
        self._artifact_repo = OperationApprovalArtifactRepository(connection_factory=self._conn)
        self._migration_repo = OperationApprovalMigrationRepository(connection_factory=self._conn)

    def _conn(self):
        return connect_sqlite(self.db_path)

    def _borrow_connection(self, conn: Any | None):
        if conn is not None:
            return conn, False
        return self._conn(), True

    def run_in_transaction(self, action) -> T:
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            result = action(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_workflow(self, operation_type: str) -> dict | None:
        return self._workflow_repo.get_workflow(operation_type)

    def list_workflows(self) -> list[dict]:
        return self._workflow_repo.list_workflows()

    def upsert_workflow(self, *, operation_type: str, name: str, steps: list[dict]) -> dict:
        return self._workflow_repo.upsert_workflow(operation_type=operation_type, name=name, steps=steps)

    def create_request(
        self,
        *,
        request_id: str,
        operation_type: str,
        workflow_name: str,
        applicant_user_id: str,
        applicant_username: str,
        company_id: int | None,
        department_id: int | None,
        target_ref: str | None,
        target_label: str | None,
        summary: dict,
        payload: dict,
        workflow_snapshot: dict,
        steps: list[dict],
        artifacts: list[dict],
        conn: Any | None = None,
    ) -> dict:
        return self._request_repo.create_request(
            request_id=request_id,
            operation_type=operation_type,
            workflow_name=workflow_name,
            applicant_user_id=applicant_user_id,
            applicant_username=applicant_username,
            company_id=company_id,
            department_id=department_id,
            target_ref=target_ref,
            target_label=target_label,
            summary=summary,
            payload=payload,
            workflow_snapshot=workflow_snapshot,
            steps=steps,
            artifacts=artifacts,
            conn=conn,
        )

    def import_request(
        self,
        *,
        request: dict,
        steps: list[dict],
        artifacts: list[dict],
        events: list[dict],
        conn: Any | None = None,
    ) -> dict:
        return self._request_repo.import_request(
            request=request,
            steps=steps,
            artifacts=artifacts,
            events=events,
            conn=conn,
        )

    def get_request(self, request_id: str, *, conn: Any | None = None) -> dict | None:
        return self._request_repo.get_request(request_id, conn=conn)

    def list_requests(
        self,
        *,
        applicant_user_id: str | None = None,
        pending_approver_user_id: str | None = None,
        related_approver_user_id: str | None = None,
        status: str | None = None,
        company_id: int | None = None,
        include_all: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        return self._request_repo.list_requests(
            applicant_user_id=applicant_user_id,
            pending_approver_user_id=pending_approver_user_id,
            related_approver_user_id=related_approver_user_id,
            status=status,
            company_id=company_id,
            include_all=include_all,
            limit=limit,
        )

    def list_request_ids_for_user(self, *, user_id: str, limit: int = 500) -> list[str]:
        return self._request_repo.list_request_ids_for_user(user_id=user_id, limit=limit)

    def get_active_step(self, *, request_id: str, conn: Any | None = None) -> dict | None:
        return self._step_repo.get_active_step(request_id=request_id, conn=conn)

    def get_step_approver(
        self,
        *,
        request_id: str,
        step_no: int,
        approver_user_id: str,
        conn: Any | None = None,
    ) -> dict | None:
        return self._step_repo.get_step_approver(
            request_id=request_id,
            step_no=step_no,
            approver_user_id=approver_user_id,
            conn=conn,
        )

    def mark_step_approver_action(
        self,
        *,
        request_id: str,
        step_no: int,
        approver_user_id: str,
        approver_username: str | None,
        status: str,
        action: str,
        notes: str | None,
        signature_id: str | None,
        conn: Any | None = None,
    ) -> None:
        self._step_repo.mark_step_approver_action(
            request_id=request_id,
            step_no=step_no,
            approver_user_id=approver_user_id,
            approver_username=approver_username,
            status=status,
            action=action,
            notes=notes,
            signature_id=signature_id,
            conn=conn,
        )

    def add_step_approver(
        self,
        *,
        request_id: str,
        request_step_id: str,
        step_no: int,
        approver_user_id: str,
        approver_username: str | None,
        conn: Any | None = None,
    ) -> None:
        self._step_repo.add_step_approver(
            request_id=request_id,
            request_step_id=request_step_id,
            step_no=step_no,
            approver_user_id=approver_user_id,
            approver_username=approver_username,
            conn=conn,
        )

    def mark_remaining_step_approvers(
        self,
        *,
        request_step_id: str,
        status: str,
        action: str,
        notes: str | None = None,
        conn: Any | None = None,
    ) -> int:
        return self._step_repo.mark_remaining_step_approvers(
            request_step_id=request_step_id,
            status=status,
            action=action,
            notes=notes,
            conn=conn,
        )

    def count_pending_approvers(self, *, request_step_id: str, conn: Any | None = None) -> int:
        return self._step_repo.count_pending_approvers(request_step_id=request_step_id, conn=conn)

    def set_step_status(
        self,
        *,
        request_step_id: str,
        status: str,
        activated: bool = False,
        completed: bool = False,
        conn: Any | None = None,
    ) -> None:
        self._step_repo.set_step_status(
            request_step_id=request_step_id,
            status=status,
            activated=activated,
            completed=completed,
            conn=conn,
        )

    def set_request_status(
        self,
        *,
        request_id: str,
        status: str,
        current_step_no: int | None = None,
        current_step_name: str | None = None,
        completed: bool = False,
        execution_started: bool = False,
        executed: bool = False,
        last_error: str | None = None,
        result_payload: dict | None = None,
        conn: Any | None = None,
    ) -> None:
        self._request_repo.set_request_status(
            request_id=request_id,
            status=status,
            current_step_no=current_step_no,
            current_step_name=current_step_name,
            completed=completed,
            execution_started=execution_started,
            executed=executed,
            last_error=last_error,
            result_payload=result_payload,
            conn=conn,
        )

    def add_event(
        self,
        *,
        request_id: str,
        event_type: str,
        actor_user_id: str | None,
        actor_username: str | None,
        step_no: int | None,
        payload: dict | None,
        conn: Any | None = None,
    ) -> dict:
        return self._event_repo.add_event(
            request_id=request_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=step_no,
            payload=payload,
            conn=conn,
        )

    def mark_artifact_cleanup(self, *, artifact_id: str, cleanup_status: str, conn: Any | None = None) -> None:
        self._artifact_repo.mark_artifact_cleanup(
            artifact_id=artifact_id,
            cleanup_status=cleanup_status,
            conn=conn,
        )

    def count_requests_by_statuses_for_company(
        self,
        *,
        statuses,
        company_id: int | None,
    ) -> dict[str, int]:
        return self._request_repo.count_requests_by_statuses_for_company(statuses=statuses, company_id=company_id)

    def count_requests_by_statuses_for_user_visibility(
        self,
        *,
        statuses,
        user_id: str,
    ) -> dict[str, int]:
        return self._request_repo.count_requests_by_statuses_for_user_visibility(statuses=statuses, user_id=user_id)

    def get_legacy_migration(self, *, legacy_instance_id: str) -> dict | None:
        return self._migration_repo.get_legacy_migration(legacy_instance_id=legacy_instance_id)

    def record_legacy_migration(
        self,
        *,
        legacy_instance_id: str,
        request_id: str | None,
        company_id: int | None,
        source_db_path: str | None,
        status: str,
        error: str | None,
    ) -> dict:
        return self._migration_repo.record_legacy_migration(
            legacy_instance_id=legacy_instance_id,
            request_id=request_id,
            company_id=company_id,
            source_db_path=source_db_path,
            status=status,
            error=error,
        )
