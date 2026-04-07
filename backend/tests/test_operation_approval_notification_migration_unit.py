from __future__ import annotations

import sqlite3
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestOperationApprovalNotificationMigrationUnit(unittest.TestCase):
    def test_ensure_schema_repairs_existing_operation_approval_todo_mojibake(self):
        td = make_temp_dir(prefix="ragflowauth_operation_approval_notification_migration")
        try:
            db_path = td / "auth.db"
            ensure_schema(db_path)

            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO notification_jobs (
                        channel_id, event_type, payload_json, recipient_user_id, recipient_username,
                        recipient_address, dedupe_key, source_job_id, status, attempts, max_attempts,
                        last_error, created_at_ms, sent_at_ms, next_retry_at_ms, read_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "inapp-main",
                        "operation_approval_todo",
                        (
                            '{"body":"鐢宠鍗?req-1 宸插埌绗?1 灞傦細第 1 层",'
                            '"title":"文件上传寰呭鎵?"}'
                        ),
                        "user-1",
                        "user1",
                        "user-1",
                        "dedupe-1",
                        None,
                        "sent",
                        0,
                        3,
                        None,
                        123,
                        124,
                        None,
                        None,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO user_inbox_notifications (
                        inbox_id, recipient_user_id, recipient_username, title, body, link_path,
                        event_type, payload_json, status, created_at_ms, read_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "inbox-1",
                        "user-1",
                        "user1",
                        "文件上传寰呭鎵?",
                        "鐢宠鍗?req-1 宸插埌绗?1 灞傦細第 1 层",
                        "/approvals?request_id=req-1",
                        "operation_approval_todo",
                        '{"body":"鐢宠鍗?req-1 宸插埌绗?1 灞傦細第 1 层","title":"文件上传寰呭鎵?"}',
                        "unread",
                        123,
                        None,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            ensure_schema(db_path)

            conn = sqlite3.connect(db_path)
            try:
                repaired_job = conn.execute(
                    "SELECT payload_json FROM notification_jobs WHERE event_type = ?",
                    ("operation_approval_todo",),
                ).fetchone()
                repaired_inbox = conn.execute(
                    """
                    SELECT title, body, payload_json
                    FROM user_inbox_notifications
                    WHERE inbox_id = ?
                    """,
                    ("inbox-1",),
                ).fetchone()
            finally:
                conn.close()

            self.assertIsNotNone(repaired_job)
            self.assertIn("文件上传待审批", repaired_job[0])
            self.assertIn("申请单 req-1 已到第 1 层：第 1 层", repaired_job[0])

            self.assertIsNotNone(repaired_inbox)
            self.assertEqual(repaired_inbox[0], "文件上传待审批")
            self.assertEqual(repaired_inbox[1], "申请单 req-1 已到第 1 层：第 1 层")
            self.assertIn("文件上传待审批", repaired_inbox[2])
            self.assertIn("申请单 req-1 已到第 1 层：第 1 层", repaired_inbox[2])
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
