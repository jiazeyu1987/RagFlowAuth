from __future__ import annotations

import unittest

from tool.maintenance.features.docker_containers_with_mounts import show_containers_with_mounts


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


class TestDockerContainersWithMountsUnit(unittest.TestCase):
    def test_reports_mount_presence(self) -> None:
        fake = _FakeSSH(
            {
                "docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'": (True, "a\timg\tUp 1h\n"),
                "docker inspect a --format '{{json .Mounts}}' 2>/dev/null || echo '[]'": (
                    True,
                    '[{\"Destination\":\"/mnt/replica\"}]',
                ),
            }
        )
        report = show_containers_with_mounts(ssh=fake, log=lambda *_: None)
        self.assertIn("a", report.text)
        self.assertIn("已挂载", report.text)

