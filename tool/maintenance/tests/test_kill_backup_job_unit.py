import unittest
from unittest.mock import patch


class TestKillBackupJobUnit(unittest.TestCase):
    def test_fails_when_backend_container_missing(self):
        from tool.maintenance.features.kill_backup_job import kill_running_backup_job

        calls = []

        def _fake_execute(self, command, callback=None, timeout_seconds=310, *, stdin_data=None):
            calls.append((command, stdin_data))
            if "docker ps -a --format" in command:
                return True, "ragflowauth-frontend\nnode-exporter\n"
            return True, ""

        with patch("tool.maintenance.features.kill_backup_job.SSHExecutor.execute", new=_fake_execute):
            res = kill_running_backup_job(server_ip="172.30.30.58", server_user="root")
            self.assertFalse(res.ok)
            self.assertIn("ragflowauth-backend container not found", res.log)
            self.assertTrue(any("docker ps -a" in c[0] for c in calls))

    def test_runs_cancel_and_restarts_backend(self):
        from tool.maintenance.features.kill_backup_job import kill_running_backup_job

        calls = []

        def _fake_execute(self, command, callback=None, timeout_seconds=310, *, stdin_data=None):
            calls.append((command, stdin_data))
            if "docker ps -a --format" in command:
                return True, "ragflowauth-backend\nragflowauth-frontend\n"
            if command.strip() == "docker exec -i ragflowauth-backend python -":
                # First docker exec is cancel/mark-failed; second is verify.
                if stdin_data and "maintenance_tool_force_kill" in stdin_data:
                    return True, '{"active_job_id": 736, "action": "cancel_requested_and_mark_failed"}'
                return True, '{"active_job_id": null}'
            if command.startswith("docker restart ragflowauth-backend"):
                return True, "ragflowauth-backend"
            return True, ""

        with patch("tool.maintenance.features.kill_backup_job.SSHExecutor.execute", new=_fake_execute):
            res = kill_running_backup_job(server_ip="172.30.30.58", server_user="root")
            self.assertTrue(res.ok)

        # Ensure we used stdin for python via docker exec.
        exec_calls = [c for c in calls if c[0].strip() == "docker exec -i ragflowauth-backend python -"]
        self.assertGreaterEqual(len(exec_calls), 2)
        self.assertTrue(any(c[1] for c in exec_calls))

        # Ensure we attempted docker restart.
        self.assertTrue(any(c[0].startswith("docker restart ragflowauth-backend") for c in calls))


if __name__ == "__main__":
    unittest.main()

