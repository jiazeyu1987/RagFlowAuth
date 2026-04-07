from __future__ import annotations

from datetime import datetime

import json


def load_config(pipeline) -> None:
    if not pipeline.ctx.config_path.exists():
        raise FileNotFoundError(f"deploy config not found: {pipeline.ctx.config_path}")

    with pipeline.ctx.config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    docker_cfg = config.get("docker", {})
    path_cfg = config.get("paths", {})

    pipeline.ctx.frontend_port = int(docker_cfg.get("frontend_port", 3001))
    pipeline.ctx.backend_port = int(docker_cfg.get("backend_port", 8001))
    pipeline.ctx.network_name = str(docker_cfg.get("network", "ragflowauth-network"))
    pipeline.ctx.data_dir = str(path_cfg.get("data_dir", "/opt/ragflowauth"))

    pipeline.ctx.server_host = pipeline.app.config.ip
    pipeline.ctx.server_user = pipeline.app.config.user

    pipeline.log(f"[DEPLOY TARGET] {pipeline.ctx.server_user}@{pipeline.ctx.server_host}")
    pipeline.log(f"[DEPLOY TARGET] environment: {pipeline.app.config.environment}")


def prepare_runtime_values(pipeline) -> None:
    pipeline.ctx.tag = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    pipeline.ctx.frontend_image = f"ragflowauth-frontend:{pipeline.ctx.tag}"
    pipeline.ctx.backend_image = f"ragflowauth-backend:{pipeline.ctx.tag}"

    temp_dir = pipeline.ctx.repo_root / "tool" / "maintenance" / "scripts" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    pipeline.ctx.temp_dir = temp_dir
    pipeline.ctx.frontend_tar = temp_dir / f"ragflowauth-frontend-{pipeline.ctx.tag}.tar"
    pipeline.ctx.backend_tar = temp_dir / f"ragflowauth-backend-{pipeline.ctx.tag}.tar"
