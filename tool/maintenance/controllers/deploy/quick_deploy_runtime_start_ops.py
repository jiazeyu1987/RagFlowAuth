from __future__ import annotations

import time

from tool.maintenance.core.constants import NAS_MOUNT_POINT


def step_6_start_containers(pipeline) -> None:
    pipeline._status("Step 6/7: starting containers...")
    pipeline.log("[Step 6/7] removing old containers")
    pipeline._run(
        [
            "ssh",
            f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}",
            "docker",
            "rm",
            "-f",
            "ragflowauth-frontend",
            "ragflowauth-backend",
        ]
    )

    pipeline._run(
        [
            "ssh",
            f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}",
            "sh",
            "-lc",
            f"docker network inspect {pipeline.ctx.network_name} >/dev/null 2>&1 || docker network create {pipeline.ctx.network_name}",
        ]
    )

    pipeline.log("[Step 6/7] starting frontend container")
    pipeline._run_or_raise(
        [
            "ssh",
            f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}",
            "docker",
            "run",
            "-d",
            "--name",
            "ragflowauth-frontend",
            "--network",
            pipeline.ctx.network_name,
            "-p",
            f"{pipeline.ctx.frontend_port}:80",
            "--restart",
            "unless-stopped",
            pipeline.ctx.frontend_image,
        ],
        error="start frontend container failed",
    )

    pipeline.log("[Step 6/7] starting backend container")
    pipeline._run_or_raise(
        [
            "ssh",
            f"{pipeline.ctx.server_user}@{pipeline.ctx.server_host}",
            "docker",
            "run",
            "-d",
            "--name",
            "ragflowauth-backend",
            "--network",
            pipeline.ctx.network_name,
            "-p",
            f"{pipeline.ctx.backend_port}:{pipeline.ctx.backend_port}",
            "-v",
            f"{pipeline.ctx.data_dir}/data:/app/data",
            "-v",
            f"{pipeline.ctx.data_dir}/uploads:/app/uploads",
            "-v",
            f"{pipeline.ctx.data_dir}/ragflow_config.json:/app/ragflow_config.json:ro",
            "-v",
            f"{pipeline.ctx.data_dir}/ragflow_compose:/app/ragflow_compose:ro",
            "-v",
            f"{NAS_MOUNT_POINT}:{NAS_MOUNT_POINT}",
            "-v",
            "/mnt/replica:/mnt/replica",
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock:ro",
            "--restart",
            "unless-stopped",
            pipeline.ctx.backend_image,
        ],
        error="start backend container failed",
    )

    time.sleep(3)
    pipeline.log("[Step 6/7] containers started")
