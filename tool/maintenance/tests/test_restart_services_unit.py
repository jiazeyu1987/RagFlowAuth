import unittest
from unittest.mock import patch


class TestRestartServicesUnit(unittest.TestCase):
    def test_prefers_compose_restart_when_compose_exists(self) -> None:
        from tool.maintenance.features.restart_services import restart_ragflow_and_ragflowauth
        from tool.maintenance.features import restart_services

        calls: list[str] = []

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            calls.append(command)
            if command.startswith("docker ps -a"):
                return True, "ragflowauth-backend\nragflowauth-frontend\nragflow_compose-ragflow-cpu-1\n"
            if command.startswith("test -f /opt/ragflowauth/ragflow_compose/docker-compose.yml"):
                return True, "/opt/ragflowauth/ragflow_compose/docker-compose.yml\n"
            if "docker compose restart" in command:
                return True, "restarted\n"
            if "docker compose up -d" in command:
                return True, "up\n"
            if "docker compose ps" in command:
                return True, "NAME   STATUS\n"
            if command.startswith("docker restart ragflowauth-backend"):
                return True, "ok\n"
            return True, ""

        with patch.object(restart_services.SSHExecutor, "execute", new=_fake_execute):
            res = restart_ragflow_and_ragflowauth(server_ip="172.30.30.58", server_user="root")

        self.assertTrue(res.ok)
        self.assertTrue(any("docker compose restart" in c for c in calls))
        self.assertTrue(any("docker compose up -d" in c for c in calls))

    def test_falls_back_to_docker_restart_when_no_compose(self) -> None:
        from tool.maintenance.features.restart_services import restart_ragflow_and_ragflowauth
        from tool.maintenance.features import restart_services

        calls: list[str] = []

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            calls.append(command)
            if command.startswith("docker ps -a"):
                return True, "ragflowauth-backend\nragflowauth-frontend\nragflow_compose-es01-1\nragflow_compose-mysql-1\n"
            if command.startswith("test -f /opt/ragflowauth/ragflow_compose/docker-compose.yml"):
                return True, "\n"
            if command.startswith("docker restart ragflow_compose-es01-1"):
                return True, "ok\n"
            if command.startswith("docker restart ragflowauth-backend"):
                return True, "ok\n"
            return True, ""

        with patch.object(restart_services.SSHExecutor, "execute", new=_fake_execute):
            res = restart_ragflow_and_ragflowauth(server_ip="172.30.30.58", server_user="root")

        self.assertTrue(res.ok)
        self.assertTrue(any(c.startswith("docker restart ragflow_compose-") for c in calls))
