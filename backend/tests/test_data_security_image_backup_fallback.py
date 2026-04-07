import unittest
from pathlib import Path
from unittest.mock import patch


class TestDataSecurityImageBackupFallback(unittest.TestCase):
    def test_list_running_container_images_filters_by_prefix(self) -> None:
        from backend.services.data_security import docker_utils

        fake = (
            "ragflow_compose-es01-1\telasticsearch:8.11.3\n"
            "other\tbusybox:latest\n"
            "ragflow_compose-ragflow-cpu-1\tinfiniflow/ragflow:v0.21.1-slim\n"
            "ragflow_compose_redis_data\tvalkey/valkey:8\n"
        )
        with patch.object(docker_utils, "run_cmd", return_value=(0, fake)):
            # Prefix may be configured as `ragflow_compose`, `ragflow_compose_`, or `ragflow_compose-`.
            images = docker_utils.list_running_container_images(name_prefix="ragflow_compose_")
        self.assertEqual(images, ["elasticsearch:8.11.3", "infiniflow/ragflow:v0.21.1-slim", "valkey/valkey:8"])

    def test_list_compose_images_filters_compose_warning_lines(self) -> None:
        from backend.services.data_security import docker_utils

        fake = (
            "elasticsearch:8.11.3\n"
            "infiniflow/ragflow:v0.22.1\n"
            'time="2026-04-07T23:49:08+08:00" level=warning msg="The \\"HOME\\" variable is not set."\n'
        )
        with patch.object(docker_utils, "run_cmd", return_value=(0, fake)):
            images, err = docker_utils.list_compose_images(Path("docker-compose.yml"))

        self.assertIsNone(err)
        self.assertEqual(images, ["elasticsearch:8.11.3", "infiniflow/ragflow:v0.22.1"])
