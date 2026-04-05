from __future__ import annotations

import unittest

from tool.maintenance.features.release_publish_runtime_ops import (
    DEFAULT_UVICORN_WORKERS,
    build_recreate_from_inspect,
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

    def test_build_recreate_does_not_inject_uvicorn_workers_for_frontend(self) -> None:
        cmd = build_recreate_from_inspect(
            "ragflowauth-frontend",
            self._inspect(["PORT=80"]),
            new_image="ragflowauth-frontend:test",
        )
        self.assertNotIn("UVICORN_WORKERS=", cmd)


if __name__ == "__main__":
    unittest.main()
