from __future__ import annotations

import unittest

from tool.maintenance.features.release_publish_runtime_ops import (
    DEFAULT_UVICORN_WORKERS,
    bootstrap_server_containers_impl,
    build_recreate_from_inspect,
    recreate_server_containers_from_inspect_impl,
)


class TestReleasePublishRuntimeOpsUnit(unittest.TestCase):
    def _inspect(self, envs: list[str]) -> dict:
        return {
            "HostConfig": {
                "NetworkMode": "bridge",
                "RestartPolicy": {"Name": "unless-stopped"},
                "PortBindings": {},
                "Binds": [],
            },
            "Config": {"Env": envs},
        }

    def test_build_recreate_adds_default_uvicorn_workers_when_missing(self) -> None:
        cmd = build_recreate_from_inspect(
            "ragflowauth-backend",
            self._inspect(["PORT=8001", "HOST=0.0.0.0"]),
            new_image="ragflowauth-backend:test",
        )
        self.assertIn(f"UVICORN_WORKERS={DEFAULT_UVICORN_WORKERS}", cmd)

    def test_build_recreate_keeps_explicit_uvicorn_workers(self) -> None:
        cmd = build_recreate_from_inspect(
            "ragflowauth-backend",
            self._inspect(["UVICORN_WORKERS=4", "PORT=8001"]),
            new_image="ragflowauth-backend:test",
        )
        self.assertIn("UVICORN_WORKERS=4", cmd)
        self.assertNotIn(f"UVICORN_WORKERS={DEFAULT_UVICORN_WORKERS}", cmd)

    def test_build_recreate_normalizes_empty_uvicorn_workers(self) -> None:
        cmd = build_recreate_from_inspect(
            "ragflowauth-backend",
            self._inspect(["UVICORN_WORKERS=", "PORT=8001"]),
            new_image="ragflowauth-backend:test",
        )
        self.assertIn(f"UVICORN_WORKERS={DEFAULT_UVICORN_WORKERS}", cmd)
        self.assertEqual(cmd.count("UVICORN_WORKERS="), 1)
        self.assertIn("/mnt/nas:/mnt/nas", cmd)

    def test_build_recreate_does_not_inject_uvicorn_workers_for_frontend(self) -> None:
        cmd = build_recreate_from_inspect(
            "ragflowauth-frontend",
            self._inspect(["PORT=80"]),
            new_image="ragflowauth-frontend:test",
        )
        self.assertNotIn("UVICORN_WORKERS=", cmd)
        self.assertNotIn("/mnt/nas:/mnt/nas", cmd)

    def test_recreate_starts_backend_before_frontend(self) -> None:
        backend_inspect = self._inspect(["PORT=8001"])
        frontend_inspect = self._inspect(["PORT=80"])
        events: list[str] = []

        def docker_inspect_fn(_ip: str, container_name: str):
            if container_name == "ragflowauth-backend":
                return backend_inspect
            if container_name == "ragflowauth-frontend":
                return frontend_inspect
            return None

        def ssh_cmd(_ip: str, command: str):
            events.append(command)
            return True, "OK"

        def ensure_network_fn(_ip: str, _network_name: str):
            return True, "OK"

        def build_recreate_fn(container_name: str, _inspect: dict, *, new_image: str):
            if container_name == "ragflowauth-backend":
                return f"CMD_BACKEND_{new_image}"
            return f"CMD_FRONTEND_{new_image}"

        def wait_ready_fn(*, prod_ip: str, healthcheck_url: str):
            _ = (prod_ip, healthcheck_url)
            events.append("WAIT_READY")
            return True, "OK"

        ok, msg = recreate_server_containers_from_inspect_impl(
            server_ip="172.30.30.58",
            backend_image="ragflowauth-backend:new",
            frontend_image="ragflowauth-frontend:new",
            healthcheck_url="http://127.0.0.1:8001/health",
            log=lambda _msg: None,
            docker_inspect_fn=docker_inspect_fn,
            ssh_cmd=ssh_cmd,
            ensure_network_fn=ensure_network_fn,
            build_recreate_fn=build_recreate_fn,
            wait_ready_fn=wait_ready_fn,
        )

        self.assertTrue(ok, msg)
        self.assertIn("CMD_BACKEND_ragflowauth-backend:new", events)
        self.assertIn("CMD_FRONTEND_ragflowauth-frontend:new", events)
        self.assertIn("WAIT_READY", events)
        self.assertLess(events.index("CMD_BACKEND_ragflowauth-backend:new"), events.index("WAIT_READY"))
        self.assertLess(events.index("WAIT_READY"), events.index("CMD_FRONTEND_ragflowauth-frontend:new"))

    def test_bootstrap_starts_backend_before_frontend(self) -> None:
        events: list[str] = []
        backend_runs: list[str] = []

        def ssh_cmd(_ip: str, command: str):
            if "test -f /opt/ragflowauth/ragflow_config.json" in command:
                return True, "OK"
            if "test -d /opt/ragflowauth/ragflow_compose" in command:
                return True, "OK"
            if "test -f /opt/ragflowauth/backup_config.json" in command:
                return True, ""
            if "docker run -d --name ragflowauth-backend" in command:
                backend_runs.append(command)
                events.append("RUN_BACKEND")
                return True, "backend_id"
            if "docker run -d --name ragflowauth-frontend" in command:
                events.append("RUN_FRONTEND")
                return True, "frontend_id"
            return True, "OK"

        def ensure_network_fn(_ip: str, _network_name: str):
            return True, "OK"

        def wait_ready_fn(*, prod_ip: str, healthcheck_url: str):
            _ = (prod_ip, healthcheck_url)
            events.append("WAIT_READY")
            return True, "OK"

        ok, msg = bootstrap_server_containers_impl(
            server_ip="172.30.30.58",
            backend_image="ragflowauth-backend:new",
            frontend_image="ragflowauth-frontend:new",
            healthcheck_url="http://127.0.0.1:8001/health",
            log=lambda _msg: None,
            ssh_cmd=ssh_cmd,
            ensure_network_fn=ensure_network_fn,
            wait_ready_fn=wait_ready_fn,
            app_dir="/opt/ragflowauth",
            network_name="ragflowauth-network",
            frontend_port=3001,
            backend_port=8001,
        )

        self.assertTrue(ok, msg)
        self.assertTrue(backend_runs)
        self.assertIn("/mnt/nas:/mnt/nas", backend_runs[0])
        self.assertIn("RUN_BACKEND", events)
        self.assertIn("RUN_FRONTEND", events)
        self.assertIn("WAIT_READY", events)
        self.assertLess(events.index("RUN_BACKEND"), events.index("WAIT_READY"))
        self.assertLess(events.index("WAIT_READY"), events.index("RUN_FRONTEND"))


if __name__ == "__main__":
    unittest.main()
