from __future__ import annotations

import time
from typing import Any

from ._base import OperationApprovalRepositoryBase


class OperationApprovalArtifactRepository(OperationApprovalRepositoryBase):
    def mark_artifact_cleanup(self, *, artifact_id: str, cleanup_status: str, conn: Any | None = None) -> None:
        now_ms = int(time.time() * 1000)
        conn, owns_conn = self._borrow_connection(conn)
        try:
            conn.execute(
                """
                UPDATE operation_approval_artifacts
                SET cleanup_status = ?, cleaned_at_ms = ?
                WHERE artifact_id = ?
                """,
                (cleanup_status, now_ms, artifact_id),
            )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn:
                conn.close()
