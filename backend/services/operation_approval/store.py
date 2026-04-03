from __future__ import annotations

import json
import time
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


def _to_json_text(value) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _from_json_text(value: str | None):
    if not value:
        return {}
    return json.loads(value)


class OperationApprovalStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

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
                approver_rows = conn.execute(
                    """
                    SELECT approver_user_id
                    FROM operation_approval_step_approvers
                    WHERE workflow_step_id = ?
                    ORDER BY approver_user_id ASC
                    """,
                    (str(step_row["workflow_step_id"]),),
                ).fetchall()
                steps.append(
                    {
                        "workflow_step_id": str(step_row["workflow_step_id"]),
                        "step_no": int(step_row["step_no"] or 0),
                        "step_name": str(step_row["step_name"]),
                        "approver_user_ids": [str(item["approver_user_id"]) for item in approver_rows if item],
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
            return [self.get_workflow(str(row["operation_type"])) for row in rows if row]
        finally:
            conn.close()

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
                for approver_user_id in item["approver_user_ids"]:
                    conn.execute(
                        """
                        INSERT INTO operation_approval_step_approvers (
                            workflow_step_approver_id, workflow_step_id, operation_type, step_no, approver_user_id, created_at_ms
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (str(uuid4()), step_id, operation_type, step_no, approver_user_id, now_ms),
                    )
            conn.commit()
        finally:
            conn.close()
        workflow = self.get_workflow(operation_type)
        if not workflow:
            raise RuntimeError("operation_approval_workflow_upsert_failed")
        return workflow

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
    ) -> dict:
        now_ms = int(time.time() * 1000)
        current_step_no = int(steps[0]["step_no"]) if steps else None
        current_step_name = str(steps[0]["step_name"]) if steps else None
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO operation_approval_requests (
                    request_id, operation_type, workflow_name, status, applicant_user_id, applicant_username,
                    target_ref, target_label, summary_json, request_payload_json, result_payload_json,
                    workflow_snapshot_json, current_step_no, current_step_name, submitted_at_ms, completed_at_ms,
                    execution_started_at_ms, executed_at_ms, last_error, company_id, department_id
                ) VALUES (?, ?, ?, 'in_approval', ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    request_id,
                    operation_type,
                    workflow_name,
                    applicant_user_id,
                    applicant_username,
                    target_ref,
                    target_label,
                    _to_json_text(summary),
                    _to_json_text(payload),
                    _to_json_text(workflow_snapshot),
                    current_step_no,
                    current_step_name,
                    now_ms,
                    company_id,
                    department_id,
                ),
            )
            for step in steps:
                request_step_id = str(uuid4())
                is_active = int(step["step_no"]) == int(current_step_no or 0)
                conn.execute(
                    """
                    INSERT INTO operation_approval_request_steps (
                        request_step_id, request_id, step_no, step_name, status, created_at_ms, activated_at_ms, completed_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        request_step_id,
                        request_id,
                        int(step["step_no"]),
                        step["step_name"],
                        "active" if is_active else "pending",
                        now_ms,
                        now_ms if is_active else None,
                    ),
                )
                for approver in step["approvers"]:
                    conn.execute(
                        """
                        INSERT INTO operation_approval_request_step_approvers (
                            request_step_approver_id, request_id, request_step_id, step_no,
                            approver_user_id, approver_username, status, action, notes, signature_id, acted_at_ms
                        ) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, NULL, NULL)
                        """,
                        (
                            str(uuid4()),
                            request_id,
                            request_step_id,
                            int(step["step_no"]),
                            approver["user_id"],
                            approver.get("username"),
                        ),
                    )
            for artifact in artifacts:
                conn.execute(
                    """
                    INSERT INTO operation_approval_artifacts (
                        artifact_id, request_id, artifact_type, file_path, file_name, mime_type, size_bytes,
                        sha256, meta_json, created_at_ms, cleaned_at_ms, cleanup_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                    """,
                    (
                        str(uuid4()),
                        request_id,
                        artifact["artifact_type"],
                        artifact["file_path"],
                        artifact.get("file_name"),
                        artifact.get("mime_type"),
                        artifact.get("size_bytes"),
                        artifact.get("sha256"),
                        _to_json_text(artifact.get("meta") or {}),
                        now_ms,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return self.get_request(request_id)

    def _request_row_to_summary(self, row) -> dict:
        return {
            "request_id": str(row["request_id"]),
            "operation_type": str(row["operation_type"]),
            "workflow_name": str(row["workflow_name"]),
            "status": str(row["status"]),
            "applicant_user_id": str(row["applicant_user_id"]),
            "applicant_username": str(row["applicant_username"]),
            "target_ref": (str(row["target_ref"]) if row["target_ref"] else None),
            "target_label": (str(row["target_label"]) if row["target_label"] else None),
            "summary": _from_json_text(row["summary_json"]),
            "payload": _from_json_text(row["request_payload_json"]),
            "result": _from_json_text(row["result_payload_json"]),
            "workflow_snapshot": _from_json_text(row["workflow_snapshot_json"]),
            "current_step_no": (int(row["current_step_no"]) if row["current_step_no"] is not None else None),
            "current_step_name": (str(row["current_step_name"]) if row["current_step_name"] else None),
            "submitted_at_ms": int(row["submitted_at_ms"] or 0),
            "completed_at_ms": (int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None),
            "execution_started_at_ms": (
                int(row["execution_started_at_ms"]) if row["execution_started_at_ms"] is not None else None
            ),
            "executed_at_ms": (int(row["executed_at_ms"]) if row["executed_at_ms"] is not None else None),
            "last_error": (str(row["last_error"]) if row["last_error"] else None),
            "company_id": (int(row["company_id"]) if row["company_id"] is not None else None),
            "department_id": (int(row["department_id"]) if row["department_id"] is not None else None),
        }

    def get_request(self, request_id: str) -> dict | None:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM operation_approval_requests WHERE request_id = ?", (request_id,)).fetchone()
            if not row:
                return None
            data = self._request_row_to_summary(row)
            step_rows = conn.execute(
                """
                SELECT request_step_id, step_no, step_name, status, created_at_ms, activated_at_ms, completed_at_ms
                FROM operation_approval_request_steps
                WHERE request_id = ?
                ORDER BY step_no ASC
                """,
                (request_id,),
            ).fetchall()
            steps: list[dict] = []
            for step_row in step_rows:
                approver_rows = conn.execute(
                    """
                    SELECT approver_user_id, approver_username, status, action, notes, signature_id, acted_at_ms
                    FROM operation_approval_request_step_approvers
                    WHERE request_step_id = ?
                    ORDER BY approver_user_id ASC
                    """,
                    (str(step_row["request_step_id"]),),
                ).fetchall()
                steps.append(
                    {
                        "request_step_id": str(step_row["request_step_id"]),
                        "step_no": int(step_row["step_no"] or 0),
                        "step_name": str(step_row["step_name"]),
                        "status": str(step_row["status"]),
                        "created_at_ms": int(step_row["created_at_ms"] or 0),
                        "activated_at_ms": (
                            int(step_row["activated_at_ms"]) if step_row["activated_at_ms"] is not None else None
                        ),
                        "completed_at_ms": (
                            int(step_row["completed_at_ms"]) if step_row["completed_at_ms"] is not None else None
                        ),
                        "approvers": [
                            {
                                "approver_user_id": str(item["approver_user_id"]),
                                "approver_username": (
                                    str(item["approver_username"]) if item["approver_username"] else None
                                ),
                                "status": str(item["status"]),
                                "action": (str(item["action"]) if item["action"] else None),
                                "notes": item["notes"],
                                "signature_id": (str(item["signature_id"]) if item["signature_id"] else None),
                                "acted_at_ms": (
                                    int(item["acted_at_ms"]) if item["acted_at_ms"] is not None else None
                                ),
                            }
                            for item in approver_rows
                            if item
                        ],
                    }
                )
            data["steps"] = steps
            event_rows = conn.execute(
                """
                SELECT event_id, event_type, actor_user_id, actor_username, step_no, payload_json, created_at_ms
                FROM operation_approval_events
                WHERE request_id = ?
                ORDER BY created_at_ms ASC, event_id ASC
                """,
                (request_id,),
            ).fetchall()
            data["events"] = [
                {
                    "event_id": str(item["event_id"]),
                    "event_type": str(item["event_type"]),
                    "actor_user_id": (str(item["actor_user_id"]) if item["actor_user_id"] else None),
                    "actor_username": (str(item["actor_username"]) if item["actor_username"] else None),
                    "step_no": (int(item["step_no"]) if item["step_no"] is not None else None),
                    "payload": _from_json_text(item["payload_json"]),
                    "created_at_ms": int(item["created_at_ms"] or 0),
                }
                for item in event_rows
                if item
            ]
            artifact_rows = conn.execute(
                """
                SELECT artifact_id, artifact_type, file_path, file_name, mime_type, size_bytes, sha256,
                       meta_json, created_at_ms, cleaned_at_ms, cleanup_status
                FROM operation_approval_artifacts
                WHERE request_id = ?
                ORDER BY created_at_ms ASC, artifact_id ASC
                """,
                (request_id,),
            ).fetchall()
            data["artifacts"] = [
                {
                    "artifact_id": str(item["artifact_id"]),
                    "artifact_type": str(item["artifact_type"]),
                    "file_path": str(item["file_path"]),
                    "file_name": (str(item["file_name"]) if item["file_name"] else None),
                    "mime_type": (str(item["mime_type"]) if item["mime_type"] else None),
                    "size_bytes": (int(item["size_bytes"]) if item["size_bytes"] is not None else None),
                    "sha256": (str(item["sha256"]) if item["sha256"] else None),
                    "meta": _from_json_text(item["meta_json"]),
                    "created_at_ms": int(item["created_at_ms"] or 0),
                    "cleaned_at_ms": (int(item["cleaned_at_ms"]) if item["cleaned_at_ms"] is not None else None),
                    "cleanup_status": (str(item["cleanup_status"]) if item["cleanup_status"] else None),
                }
                for item in artifact_rows
                if item
            ]
            return data
        finally:
            conn.close()

    def list_requests(
        self,
        *,
        applicant_user_id: str | None = None,
        pending_approver_user_id: str | None = None,
        include_all: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        lim = max(1, min(500, int(limit)))
        query = """
            SELECT *
            FROM operation_approval_requests
            WHERE 1 = 1
        """
        params: list[object] = []
        if applicant_user_id:
            query += " AND applicant_user_id = ?"
            params.append(applicant_user_id)
        if pending_approver_user_id:
            query += """
                AND EXISTS (
                    SELECT 1
                    FROM operation_approval_request_step_approvers rsa
                    JOIN operation_approval_request_steps rs ON rs.request_step_id = rsa.request_step_id
                    WHERE rsa.request_id = operation_approval_requests.request_id
                      AND rsa.approver_user_id = ?
                      AND rsa.status = 'pending'
                      AND rs.status = 'active'
                )
            """
            params.append(pending_approver_user_id)
        if not include_all and not applicant_user_id and not pending_approver_user_id:
            return []
        query += " ORDER BY submitted_at_ms DESC LIMIT ?"
        params.append(lim)
        conn = self._conn()
        try:
            rows = conn.execute(query, params).fetchall()
            return [self._request_row_to_summary(row) for row in rows if row]
        finally:
            conn.close()

    def list_request_ids_for_user(self, *, user_id: str, limit: int = 500) -> list[str]:
        lim = max(1, min(1000, int(limit)))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT request_id
                FROM operation_approval_request_step_approvers
                WHERE approver_user_id = ?
                ORDER BY request_id DESC
                LIMIT ?
                """,
                (user_id, lim),
            ).fetchall()
            return [str(row["request_id"]) for row in rows if row]
        finally:
            conn.close()

    def get_active_step(self, *, request_id: str) -> dict | None:
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT request_step_id, step_no, step_name, status, created_at_ms, activated_at_ms, completed_at_ms
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
                "status": str(row["status"]),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "activated_at_ms": (int(row["activated_at_ms"]) if row["activated_at_ms"] is not None else None),
                "completed_at_ms": (int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None),
            }
        finally:
            conn.close()

    def get_step_approver(self, *, request_id: str, step_no: int, approver_user_id: str) -> dict | None:
        conn = self._conn()
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
        signature_id: str,
    ) -> None:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
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
            conn.commit()
        finally:
            conn.close()

    def count_pending_approvers(self, *, request_step_id: str) -> int:
        conn = self._conn()
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
            conn.close()

    def set_step_status(self, *, request_step_id: str, status: str, activated: bool = False, completed: bool = False) -> None:
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
        conn = self._conn()
        try:
            conn.execute(
                f"""
                UPDATE operation_approval_request_steps
                SET {", ".join(updates)}
                WHERE request_step_id = ?
                """,
                params,
            )
            conn.commit()
        finally:
            conn.close()

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
    ) -> None:
        now_ms = int(time.time() * 1000)
        updates = ["status = ?", "current_step_no = ?", "current_step_name = ?", "last_error = ?", "result_payload_json = ?"]
        params: list[object] = [
            status,
            current_step_no,
            current_step_name,
            last_error,
            (_to_json_text(result_payload) if result_payload is not None else None),
        ]
        if completed:
            updates.append("completed_at_ms = ?")
            params.append(now_ms)
        if execution_started:
            updates.append("execution_started_at_ms = ?")
            params.append(now_ms)
        if executed:
            updates.append("executed_at_ms = ?")
            params.append(now_ms)
        params.append(request_id)
        conn = self._conn()
        try:
            conn.execute(
                f"""
                UPDATE operation_approval_requests
                SET {", ".join(updates)}
                WHERE request_id = ?
                """,
                params,
            )
            conn.commit()
        finally:
            conn.close()

    def add_event(
        self,
        *,
        request_id: str,
        event_type: str,
        actor_user_id: str | None,
        actor_username: str | None,
        step_no: int | None,
        payload: dict | None,
    ) -> dict:
        event_id = str(uuid4())
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO operation_approval_events (
                    event_id, request_id, event_type, actor_user_id, actor_username, step_no, payload_json, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, request_id, event_type, actor_user_id, actor_username, step_no, _to_json_text(payload), now_ms),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "event_id": event_id,
            "request_id": request_id,
            "event_type": event_type,
            "actor_user_id": actor_user_id,
            "actor_username": actor_username,
            "step_no": step_no,
            "payload": payload or {},
            "created_at_ms": now_ms,
        }

    def mark_artifact_cleanup(self, *, artifact_id: str, cleanup_status: str) -> None:
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE operation_approval_artifacts
                SET cleanup_status = ?, cleaned_at_ms = ?
                WHERE artifact_id = ?
                """,
                (cleanup_status, now_ms, artifact_id),
            )
            conn.commit()
        finally:
            conn.close()
