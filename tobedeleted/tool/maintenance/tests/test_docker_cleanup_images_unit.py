from __future__ import annotations

import unittest

from tool.maintenance.features.docker_cleanup_images import cleanup_docker_images


class _FakeSSH:
    def __init__(self, responses: dict[str, tuple[bool, str]]):
        self.responses = responses
        self.calls: list[str] = []

    def execute(self, command: str, callback=None, timeout_seconds: int = 0):
        self.calls.append(command)
        ok, out = self.responses.get(command, (True, ""))
        if callback:
            callback(out)
        return ok, out


class TestDockerCleanupImagesUnit(unittest.TestCase):
    def test_selects_unused_images_to_delete(self) -> None:
        fake = _FakeSSH(
            {
                "docker ps --format '{{.Image}}'": (True, "ragflowauth-backend:1.0.0\n"),
                "docker images ragflowauth-backend --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | head -n 1 || true": (
                    True,
                    "ragflowauth-backend:1.0.0\n",
                ),
                "docker images ragflowauth-frontend --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | head -n 1 || true": (
                    True,
                    "ragflowauth-frontend:1.0.0\n",
                ),
                "docker images --format '{{.Repository}}:{{.Tag}}' | grep 'ragflowauth' || echo 'NO_IMAGES'": (
                    True,
                    "ragflowauth-backend:1.0.0\nragflowauth-backend:0.9.0\nragflowauth-frontend:1.0.0\nragflowauth-frontend:0.9.0\n",
                ),
                "docker rmi ragflowauth-backend:0.9.0 2>&1 || echo 'FAILED'": (True, "Untagged\n"),
                "docker rmi ragflowauth-frontend:0.9.0 2>&1 || echo 'FAILED'": (True, "Untagged\n"),
                "docker system df 2>&1 || true": (True, "TYPE TOTAL ACTIVE\n"),
            }
        )

        res = cleanup_docker_images(ssh=fake, log=lambda *_: None, keep_last_n=1)
        self.assertEqual(res.deleted, ["ragflowauth-backend:0.9.0", "ragflowauth-frontend:0.9.0"])
        self.assertEqual(res.failed, [])
