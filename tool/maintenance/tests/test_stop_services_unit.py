import unittest
from unittest.mock import patch


class TestStopServicesUnit(unittest.TestCase):
    def test_prefers_compose_stop_when_compose_exists(self) -> None:
        from tool.maintenance.features.stop_services import stop_ragflow_and_ragflowauth
        from tool.maintenance.features import stop_services

        calls: list[str] = []

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            calls.append(command)
            if command.startswith("docker ps -a"):
                return True, "ragflowauth-backend\nragflowauth-frontend\nragflow_compose-ragflow-cpu-1\n"
            if command.startswith("test -f /opt/ragflowauth/ragflow_compose/docker-compose.yml"):
                return True, "/opt/ragflowauth/ragflow_compose/docker-compose.yml\n"
            if "docker compose stop" in command:
                return True, "stopped\n"
            if "docker compose ps" in command:
                return True, "NAME   STATUS\n"
            if command.startswith("docker stop ragflowauth-backend"):
                return True, "ok\n"
            return True, ""

        with patch.object(stop_services.SSHExecutor, "execute", new=_fake_execute):
            res = stop_ragflow_and_ragflowauth(server_ip="172.30.30.58", server_user="root")

        self.assertTrue(res.ok)
        self.assertTrue(any("docker compose stop" in c for c in calls))

    def test_falls_back_to_docker_stop_when_no_compose(self) -> None:
        from tool.maintenance.features.stop_services import stop_ragflow_and_ragflowauth
        from tool.maintenance.features import stop_services

        calls: list[str] = []

        def _fake_execute(_self, command, callback=None, timeout_seconds=310, *, stdin_data=None):  # noqa: ARG001
            calls.append(command)
            if command.startswith("docker ps -a"):
                return True, "ragflowauth-backend\nragflowauth-frontend\nragflow_compose-es01-1\nragflow_compose-mysql-1\n"
            if command.startswith("test -f /opt/ragflowauth/ragflow_compose/docker-compose.yml"):
                return True, "\n"
            if command.startswith("docker stop ragflow_compose-es01-1"):
                return True, "ok\n"
            if command.startswith("docker stop ragflowauth-backend"):
                return True, "ok\n"
            return True, ""

        with patch.object(stop_services.SSHExecutor, "execute", new=_fake_execute):
            res = stop_ragflow_and_ragflowauth(server_ip="172.30.30.58", server_user="root")

        self.assertTrue(res.ok)
        self.assertTrue(any(c.startswith("docker stop ragflow_compose-") for c in calls))

