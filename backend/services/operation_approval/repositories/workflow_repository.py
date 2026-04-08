from __future__ import annotations

import time
from uuid import uuid4

from ._base import OperationApprovalRepositoryBase


class OperationApprovalWorkflowRepository(OperationApprovalRepositoryBase):
    def get_workflow(self, operation_type: str) -> dict | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT operation_type, name, is_active, created_at_ms, updated_at_ms
                FROM operation_approval_workflows
                WHERE operation_type = ?
                """,
                (operation_type,),
            ).fetchone()
            if not row:
                return None
            step_rows = conn.execute(
                """
                SELECT workflow_step_id, step_no, step_name, created_at_ms
                FROM operation_approval_workflow_steps
                WHERE operation_type = ?
                ORDER BY step_no ASC
                """,
                (operation_type,),
            ).fetchall()
            steps: list[dict] = []
            for step_row in step_rows:
                member_rows = conn.execute(
                    """
                    SELECT approver_user_id, member_type, member_ref
                    FROM operation_approval_step_approvers
                    WHERE workflow_step_id = ?
                    ORDER BY rowid ASC
                    """,
                    (str(step_row["workflow_step_id"]),),
                ).fetchall()
                members: list[dict] = []
                for item in member_rows:
                    if not item:
                        continue
                    member_type = str(item["member_type"] or "").strip() or "user"
                    member_ref = str(item["member_ref"] or "").strip() or str(item["approver_user_id"] or "").strip()
                    if not member_ref:
                        continue
                    members.append({"member_type": member_type, "member_ref": member_ref})
                steps.append(
                    {
                        "workflow_step_id": str(step_row["workflow_step_id"]),
                        "step_no": int(step_row["step_no"] or 0),
                        "step_name": str(step_row["step_name"]),
                        "members": members,
                        "created_at_ms": int(step_row["created_at_ms"] or 0),
                    }
                )
            return {
                "operation_type": str(row["operation_type"]),
                "name": str(row["name"]),
                "is_active": bool(row["is_active"]),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
                "steps": steps,
            }
        finally:
            conn.close()

    def list_workflows(self) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT operation_type
                FROM operation_approval_workflows
                ORDER BY operation_type ASC
                """
            ).fetchall()
        finally:
            conn.close()
        items: list[dict] = []
        for row in rows:
            workflow = self.get_workflow(str(row["operation_type"]))
            if workflow is not None:
                items.append(workflow)
        return items

    def upsert_workflow(self, *, operation_type: str, name: str, steps: list[dict]) -> dict:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO operation_approval_workflows (
                    operation_type, name, is_active, created_at_ms, updated_at_ms
                ) VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(operation_type) DO UPDATE SET
                    name = excluded.name,
                    is_active = 1,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (operation_type, name, now_ms, now_ms),
            )
            conn.execute("DELETE FROM operation_approval_step_approvers WHERE operation_type = ?", (operation_type,))
            conn.execute("DELETE FROM operation_approval_workflow_steps WHERE operation_type = ?", (operation_type,))
            for item in steps:
                step_id = str(uuid4())
                step_no = int(item["step_no"])
                conn.execute(
                    """
                    INSERT INTO operation_approval_workflow_steps (
                        workflow_step_id, operation_type, step_no, step_name, created_at_ms
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (step_id, operation_type, step_no, item["step_name"], now_ms),
                )
                members = list(item.get("members") or [])
                if not members and item.get("approver_user_ids"):
                    members = [
                        {"member_type": "user", "member_ref": str(approver_user_id)}
                        for approver_user_id in item.get("approver_user_ids") or []
                    ]
                for member in members:
                    member_type = str(member["member_type"])
                    member_ref = str(member["member_ref"])
                    conn.execute(
                        """
                        INSERT INTO operation_approval_step_approvers (
                            workflow_step_approver_id, workflow_step_id, operation_type, step_no,
                            approver_user_id, member_type, member_ref, created_at_ms
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (str(uuid4()), step_id, operation_type, step_no, member_ref, member_type, member_ref, now_ms),
                    )
            conn.commit()
        finally:
            conn.close()
        workflow = self.get_workflow(operation_type)
        if not workflow:
            raise RuntimeError("operation_approval_workflow_upsert_failed")
        return workflow
