import unittest
from unittest.mock import patch


class TestCancelBackupJobUnit(unittest.TestCase):
    def test_calls_docker_exec_and_parses_json(self) -> None:
        from tool.maintenance.features import cancel_backup_job

        tc = self

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            tc.assertEqual(command, "docker exec -i ragflowauth-backend python -")
            tc.assertIn("request_cancel_job", stdin_data or "")
            return True, '{"ok": true, "job_id": 123, "status": "canceling", "message": "cancel_requested"}'

        with patch.object(cancel_backup_job.SSHExecutor, "execute", new=_fake_execute):
            res = cancel_backup_job.cancel_active_backup_job(server_ip="172.30.30.58", server_user="root", wait_seconds=0)

        self.assertTrue(res.ok)
        self.assertEqual(res.job_id, 123)
        self.assertEqual(res.status, "canceling")
        self.assertFalse(res.final)
        self.assertEqual(res.waited_seconds, 0)

    def test_polling_until_terminal_status(self) -> None:
        from tool.maintenance.features import cancel_backup_job

        responses = [
            (True, '{"ok": true, "job_id": 123, "status": "canceling", "message": "cancel_requested"}'),
            (True, '{"ok": true, "job_id": 123, "status": "canceling", "message": "stopping", "progress": 10}'),
            (True, '{"ok": true, "job_id": 123, "status": "canceled", "message": "done", "progress": 100}'),
        ]
        calls = {"n": 0}

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            self.assertEqual(command, "docker exec -i ragflowauth-backend python -")
            idx = calls["n"]
            calls["n"] += 1
            ok, out = responses[min(idx, len(responses) - 1)]
            # Ensure the polling script uses get_job after the first call.
            if idx == 0:
                self.assertIn("request_cancel_job", stdin_data or "")
            else:
                self.assertIn("get_job", stdin_data or "")
            return ok, out

        with (
            patch.object(cancel_backup_job.SSHExecutor, "execute", new=_fake_execute),
            patch.object(cancel_backup_job, "sleep", new=lambda *_a, **_k: None),
        ):
            res = cancel_backup_job.cancel_active_backup_job(
                server_ip="172.30.30.58",
                server_user="root",
                wait_seconds=10,
                poll_interval_seconds=2,
            )

        self.assertTrue(res.ok)
        self.assertEqual(res.job_id, 123)
        self.assertEqual(res.status, "canceled")
        self.assertTrue(res.final)
        self.assertGreaterEqual(res.waited_seconds, 2)
