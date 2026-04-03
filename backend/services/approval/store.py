from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


class ApprovalWorkflowStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _normalize_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in steps or []:
            step_no = int(item.get("step_no"))
            step_name = str(item.get("step_name") or "").strip()
            approver_user_id = str(item.get("approver_user_id") or "").strip() or None
            approver_role = str(item.get("approver_role") or "").strip() or None
            approver_group_id = item.get("approver_group_id")
            approver_department_id = item.get("approver_department_id")
            approver_company_id = item.get("approver_company_id")
            approval_mode = str(item.get("approval_mode") or "all").strip().lower() or "all"
            if step_no <= 0 or not step_name:
                raise ValueError("invalid_workflow_step")
            if approval_mode not in {"all", "any"}:
                raise ValueError("invalid_workflow_approval_mode")
            if approver_group_id is not None:
                approver_group_id = int(approver_group_id)
            if approver_department_id is not None:
                approver_department_id = int(approver_department_id)
            if approver_company_id is not None:
                approver_company_id = int(approver_company_id)
            if not any(
                value is not None
                for value in (
                    approver_user_id,
                    approver_role,
                    approver_group_id,
                    approver_department_id,
                    approver_company_id,
                )
            ):
                raise ValueError("workflow_step_approver_required")
            normalized.append(
                {
                    "step_no": step_no,
                    "step_name": step_name,
                    "approver_user_id": approver_user_id,
                    "approver_role": approver_role,
                    "approver_group_id": approver_group_id,
                    "approver_department_id": approver_department_id,
                    "approver_company_id": approver_company_id,
                    "approval_mode": approval_mode,
                }
            )
        normalized.sort(key=lambda x: x["step_no"])
        expected = list(range(1, len(normalized) + 1))
        actual = [it["step_no"] for it in normalized]
        if actual != expected:
            raise ValueError("invalid_workflow_step_sequence")
        return normalized

    def upsert_workflow(
        self,
        *,
        workflow_id: str,
        kb_ref: str,
        name: str,
        steps: list[dict[str, Any]],
        is_active: bool = True,
    ) -> dict[str, Any]:
        workflow_id = str(workflow_id or "").strip()
        kb_ref = str(kb_ref or "").strip()
        name = str(name or "").strip()
        if not workflow_id:
            raise ValueError("workflow_id_required")
        if not kb_ref:
            raise ValueError("kb_ref_required")
        if not name:
            raise ValueError("workflow_name_required")
        normalized_steps = self._normalize_steps(steps)
        now_ms = int(time.time() * 1000)

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT workflow_id FROM approval_workflows WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE approval_workflows
                    SET kb_ref = ?, name = ?, is_active = ?, updated_at_ms = ?
                    WHERE workflow_id = ?
                    """,
                    (kb_ref, name, 1 if is_active else 0, now_ms, workflow_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO approval_workflows (workflow_id, kb_ref, name, is_active, created_at_ms, updated_at_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (workflow_id, kb_ref, name, 1 if is_active else 0, now_ms, now_ms),
                )
            conn.execute("DELETE FROM approval_workflow_steps WHERE workflow_id = ?", (workflow_id,))
            for step in normalized_steps:
                conn.execute(
                    """
                    INSERT INTO approval_workflow_steps (
                        step_id,
                        workflow_id,
                        step_no,
                        step_name,
                        approver_user_id,
                        approver_role,
                        approver_group_id,
                        approver_department_id,
                        approver_company_id,
                        approval_mode,
                        created_at_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        workflow_id,
                        int(step["step_no"]),
                        str(step["step_name"]),
                        step["approver_user_id"],
                        step["approver_role"],
                        step["approver_group_id"],
                        step["approver_department_id"],
                        step["approver_company_id"],
                        step["approval_mode"],
                        now_ms,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return self.get_workflow(workflow_id)

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT workflow_id, kb_ref, name, is_active, created_at_ms, updated_at_ms
                FROM approval_workflows
                WHERE workflow_id = ?
                """,
                (workflow_id,),
            ).fetchone()
            if not row:
                return None
            steps = conn.execute(
                """
                SELECT
                    step_no,
                    step_name,
                    approver_user_id,
                    approver_role,
                    approver_group_id,
                    approver_department_id,
                    approver_company_id,
                    approval_mode
                FROM approval_workflow_steps
                WHERE workflow_id = ?
                ORDER BY step_no ASC
                """,
                (workflow_id,),
            ).fetchall()
            return {
                "workflow_id": row["workflow_id"],
                "kb_ref": row["kb_ref"],
                "name": row["name"],
                "is_active": bool(row["is_active"]),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
                "steps": [
                    {
                        "step_no": int(s["step_no"]),
                        "step_name": s["step_name"],
                        "approver_user_id": (str(s["approver_user_id"]) if s["approver_user_id"] else None),
                        "approver_role": (str(s["approver_role"]) if s["approver_role"] else None),
                        "approver_group_id": (
                            int(s["approver_group_id"]) if s["approver_group_id"] is not None else None
                        ),
                        "approver_department_id": (
                            int(s["approver_department_id"]) if s["approver_department_id"] is not None else None
                        ),
                        "approver_company_id": (
                            int(s["approver_company_id"]) if s["approver_company_id"] is not None else None
                        ),
                        "approval_mode": str(s["approval_mode"] or "all"),
                    }
                    for s in steps
                ],
            }
        finally:
            conn.close()

    def list_workflows(self, *, kb_ref: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            if kb_ref:
                rows = conn.execute(
                    """
                    SELECT workflow_id
                    FROM approval_workflows
                    WHERE kb_ref = ?
                    ORDER BY updated_at_ms DESC
                    """,
                    (kb_ref,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT workflow_id
                    FROM approval_workflows
                    ORDER BY updated_at_ms DESC
                    """
                ).fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                item = self.get_workflow(str(row["workflow_id"]))
                if item:
                    out.append(item)
            return out
        finally:
            conn.close()

    def find_active_workflow_by_refs(self, kb_refs: list[str]) -> dict[str, Any] | None:
        refs = [str(r).strip() for r in kb_refs if str(r or "").strip()]
        if not refs:
            return None
        placeholders = ",".join("?" for _ in refs)
        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT workflow_id, kb_ref
                FROM approval_workflows
                WHERE is_active = 1
                  AND kb_ref IN ({placeholders})
                ORDER BY updated_at_ms DESC
                """,
                refs,
            ).fetchall()
            if not rows:
                return None
            by_ref: dict[str, str] = {}
            for row in rows:
                by_ref[str(row["kb_ref"])] = str(row["workflow_id"])
            for ref in refs:
                if ref in by_ref:
                    return self.get_workflow(by_ref[ref])
            return self.get_workflow(str(rows[0]["workflow_id"]))
        finally:
            conn.close()

    def get_instance_by_doc_id(self, doc_id: str) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT instance_id, doc_id, workflow_id, current_step_no, status, started_at_ms, completed_at_ms
                FROM document_approval_instances
                WHERE doc_id = ?
                """,
                (doc_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "instance_id": row["instance_id"],
                "doc_id": row["doc_id"],
                "workflow_id": row["workflow_id"],
                "current_step_no": int(row["current_step_no"] or 0),
                "status": row["status"],
                "started_at_ms": int(row["started_at_ms"] or 0),
                "completed_at_ms": (int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None),
            }
        finally:
            conn.close()

    def create_instance(self, *, doc_id: str, workflow_id: str) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        instance_id = str(uuid4())
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO document_approval_instances (
                    instance_id, doc_id, workflow_id, current_step_no, status, started_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (instance_id, doc_id, workflow_id, 1, "in_progress", now_ms),
            )
            conn.commit()
        finally:
            conn.close()
        item = self.get_instance_by_doc_id(doc_id)
        if item is None:
            raise RuntimeError("approval_instance_create_failed")
        return item

    def advance_instance(self, *, instance_id: str, next_step_no: int) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE document_approval_instances
                SET current_step_no = ?, status = 'in_progress'
                WHERE instance_id = ?
                """,
                (int(next_step_no), instance_id),
            )
            conn.commit()
        finally:
            conn.close()

    def complete_instance(self, *, instance_id: str, status: str) -> None:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE document_approval_instances
                SET status = ?, completed_at_ms = ?
                WHERE instance_id = ?
                """,
                (status, now_ms, instance_id),
            )
            conn.commit()
        finally:
            conn.close()

    def record_action(
        self,
        *,
        instance_id: str,
        doc_id: str,
        workflow_id: str,
        step_no: int,
        action: str,
        actor: str,
        notes: str | None,
    ) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        action_id = str(uuid4())
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO document_approval_actions (
                    action_id, instance_id, doc_id, workflow_id, step_no, action, actor, notes, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (action_id, instance_id, doc_id, workflow_id, int(step_no), action, actor, notes, now_ms),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "action_id": action_id,
            "instance_id": instance_id,
            "doc_id": doc_id,
            "workflow_id": workflow_id,
            "step_no": int(step_no),
            "action": action,
            "actor": actor,
            "notes": notes,
            "created_at_ms": now_ms,
        }

    def list_instances_by_doc_ids(self, doc_ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = [str(x).strip() for x in doc_ids if str(x or "").strip()]
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT instance_id, doc_id, workflow_id, current_step_no, status, started_at_ms, completed_at_ms
                FROM document_approval_instances
                WHERE doc_id IN ({placeholders})
                """,
                ids,
            ).fetchall()
            out: dict[str, dict[str, Any]] = {}
            for row in rows:
                out[str(row["doc_id"])] = {
                    "instance_id": row["instance_id"],
                    "doc_id": row["doc_id"],
                    "workflow_id": row["workflow_id"],
                    "current_step_no": int(row["current_step_no"] or 0),
                    "status": row["status"],
                    "started_at_ms": int(row["started_at_ms"] or 0),
                    "completed_at_ms": (int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None),
                }
            return out
        finally:
            conn.close()
