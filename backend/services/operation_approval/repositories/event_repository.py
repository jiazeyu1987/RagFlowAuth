from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from ._base import OperationApprovalRepositoryBase
from ._shared import to_json_text


class OperationApprovalEventRepository(OperationApprovalRepositoryBase):
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
        event_id = str(uuid4())
        now_ms = int(time.time() * 1000)
        conn, owns_conn = self._borrow_connection(conn)
        try:
            conn.execute(
                """
                INSERT INTO operation_approval_events (
                    event_id, request_id, event_type, actor_user_id, actor_username, step_no, payload_json, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, request_id, event_type, actor_user_id, actor_username, step_no, to_json_text(payload), now_ms),
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
