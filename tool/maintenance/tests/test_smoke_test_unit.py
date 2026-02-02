import unittest
from unittest.mock import patch

from tool.maintenance.features.smoke_test import feature_run_smoke_test
from tool.maintenance.core import ssh_executor


class TestSmokeTestUnit(unittest.TestCase):
    def test_report_contains_expected_sections(self):
        def fake_execute(self, command: str, callback=None, timeout_seconds: int = 310, *, stdin_data=None):
            if "docker --version" in command:
                return True, "Docker version 26.0.0"
            if "docker ps" in command:
                return True, "ragflowauth-backend\tragflowauth-backend:tag\tUp 1 minute"
            if "curl -fsS http://127.0.0.1:8001/health" in command:
                return True, "OK"
            if "curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/" in command:
                return True, "200"
            if "curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:9380/" in command:
                return True, "200"
            if "mount | grep -E '/mnt/replica'" in command:
                return True, "//host/share on /mnt/replica type cifs\n---\nFilesystem      Size  Used Avail Use% Mounted on\n..."
            if "df -h /opt/ragflowauth" in command:
                return True, "Filesystem      Size  Used Avail Use% Mounted on\n..."
            return False, "unknown"

        with patch.object(ssh_executor.SSHExecutor, "execute", new=fake_execute):
            res = feature_run_smoke_test(server_ip="172.30.30.58")

        self.assertIn("SMOKE server=172.30.30.58", res.report)
        self.assertTrue(res.ok)
