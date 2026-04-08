from __future__ import annotations

import time
from typing import Any

from ._base import OperationApprovalRepositoryBase


class OperationApprovalStepRepository(OperationApprovalRepositoryBase):
    def get_active_step(self, *, request_id: str, conn: Any | None = None) -> dict | None:
        conn, owns_conn = self._borrow_connection(conn)
        try:
            row = conn.execute(
                """
                SELECT request_step_id, step_no, step_name, approval_rule, status, created_at_ms, activated_at_ms, completed_at_ms
                FROM operation_approval_request_steps
                WHERE request_id = ? AND status = 'active'
                ORDER BY step_no ASC
                LIMIT 1
                """,
                (request_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "request_step_id": str(row["request_step_id"]),
                "step_no": int(row["step_no"] or 0),
                "step_name": str(row["step_name"]),
                "approval_rule": str(row["approval_rule"] or "all"),
                "status": str(row["status"]),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "activated_at_ms": (int(row["activated_at_ms"]) if row["activated_at_ms"] is not None else None),
                "completed_at_ms": (int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None),
            }
        finally:
            if owns_conn:
                conn.close()

    def get_step_approver(
        self,
        *,
        request_id: str,
        step_no: int,
        approver_user_id: str,
        conn: Any | None = None,
    ) -> dict | None:
        conn, owns_conn = self._borrow_connection(conn)
        try:
            row = conn.execute(
                """
                SELECT request_step_approver_id, approver_user_id, approver_username, status, action, notes, signature_id, acted_at_ms
                FROM operation_approval_request_step_approvers
                WHERE request_id = ? AND step_no = ? AND approver_user_id = ?
                LIMIT 1
                """,
                (request_id, int(step_no), approver_user_id),
            ).fetchone()
            if not row:
                return None
            return {
                "request_step_approver_id": str(row["request_step_approver_id"]),
                "approver_user_id": str(row["approver_user_id"]),
                "approver_username": (str(row["approver_username"]) if row["approver_username"] else None),
                "status": str(row["status"]),
                "action": (str(row["action"]) if row["action"] else None),
                "notes": row["notes"],
                "signature_id": (str(row["signature_id"]) if row["signature_id"] else None),
                "acted_at_ms": (int(row["acted_at_ms"]) if row["acted_at_ms"] is not None else None),
            }
        finally:
            if owns_conn:
                conn.close()

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
        now_ms = int(time.time() * 1000)
        conn, owns_conn = self._borrow_connection(conn)
        try:
            conn.execute(
                """
                UPDATE operation_approval_request_step_approvers
                SET
                    approver_username = COALESCE(?, approver_username),
                    status = ?,
                    action = ?,
                    notes = ?,
                    signature_id = ?,
                    acted_at_ms = ?
                WHERE request_id = ? AND step_no = ? AND approver_user_id = ?
                """,
                (
                    approver_username,
                    status,
                    action,
                    notes,
                    signature_id,
                    now_ms,
                    request_id,
                    int(step_no),
                    approver_user_id,
                ),
            )
            if owns_conn:
                conn.commit()
        except Exception:
            if owns_conn:
                conn.rollback()
            raise
        finally:
            if owns_conn:
                conn.close()

    def mark_remaining_step_approvers(
        self,
        *,
        request_step_id: str,
        status: str,
        action: str,
        notes: str | None = None,
        conn: Any | None = None,
    ) -> int:
        now_ms = int(time.time() * 1000)
        conn, owns_conn = self._borrow_connection(conn)
        try:
            cur = conn.execute(
                """
                UPDATE operation_approval_request_step_approvers
                SET status = ?, action = ?, notes = ?, acted_at_ms = ?
                WHERE request_step_id = ? AND status = 'pending'
                """,
                (status, action, notes, now_ms, request_step_id),
            )
            if owns_conn:
                conn.commit()
            return int(cur.rowcount or 0)
        except Exception:
            if owns_conn:
                conn.rollback()
            raise
        finally:
            if owns_conn:
                conn.close()

    def count_pending_approvers(self, *, request_step_id: str, conn: Any | None = None) -> int:
        conn, owns_conn = self._borrow_connection(conn)
        try:
            row = conn.execute(
                """
                SELECT COUNT(1) AS c
                FROM operation_approval_request_step_approvers
                WHERE request_step_id = ? AND status = 'pending'
                """,
                (request_step_id,),
            ).fetchone()
            return int(row["c"] or 0) if row else 0
        finally:
            if owns_conn:
                conn.close()

    def set_step_status(
        self,
        *,
        request_step_id: str,
        status: str,
        activated: bool = False,
        completed: bool = False,
        conn: Any | None = None,
    ) -> None:
        now_ms = int(time.time() * 1000)
        updates = ["status = ?"]
        params: list[object] = [status]
        if activated:
            updates.append("activated_at_ms = COALESCE(activated_at_ms, ?)")
            params.append(now_ms)
        if completed:
            updates.append("completed_at_ms = ?")
            params.append(now_ms)
        params.append(request_step_id)
        conn, owns_conn = self._borrow_connection(conn)
        try:
            conn.execute(
                f"""
                UPDATE operation_approval_request_steps
                SET {", ".join(updates)}
                WHERE request_step_id = ?
                """,
                params,
            )
            if owns_conn:
                conn.commit()
        except Exception:
            if owns_conn:
                conn.rollback()
            raise
        finally:
            if owns_conn:
                conn.close()
