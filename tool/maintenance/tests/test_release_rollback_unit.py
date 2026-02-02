from __future__ import annotations

import unittest
from unittest.mock import patch

from tool.maintenance.features import release_rollback
from tool.maintenance.features import release_publish as rp


class TestReleaseRollbackUnit(unittest.TestCase):
    def test_rollback_uses_inspect_recreate_and_healthcheck(self):
        inspect_backend = {"HostConfig": {"NetworkMode": "ragflowauth-network"}}
        inspect_frontend = {"HostConfig": {"NetworkMode": "ragflowauth-network"}}

        calls: list[str] = []

        def fake_ssh_cmd(ip: str, command: str):
            calls.append(command)
            return True, "OK"

        with patch.object(rp, "_docker_inspect", side_effect=[inspect_backend, inspect_frontend]), patch.object(
            rp, "_ensure_network", return_value=(True, "")
        ), patch.object(rp, "_ssh_cmd", side_effect=fake_ssh_cmd), patch.object(
            rp, "_build_recreate_from_inspect", side_effect=["RUN_FE", "RUN_BE"]
        ), patch.object(
            rp, "_wait_prod_ready", return_value=(True, "OK")
        ):
            res = release_rollback.feature_rollback_ragflowauth_to_version(server_ip="172.30.30.57", version="v1")

        self.assertTrue(res.ok, res.log)
        self.assertIn("docker stop ragflowauth-backend ragflowauth-frontend", "\n".join(calls))
        self.assertIn("docker rm -f ragflowauth-backend ragflowauth-frontend", "\n".join(calls))
        self.assertIn("RUN_FE", "\n".join(calls))
        self.assertIn("RUN_BE", "\n".join(calls))

