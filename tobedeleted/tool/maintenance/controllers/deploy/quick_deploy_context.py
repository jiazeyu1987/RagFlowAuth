from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class QuickDeployContext:
    app: object
    subprocess: object
    log_to_file: object
    repo_root: Path
    config_path: Path

    server_host: str = ""
    server_user: str = ""
    frontend_port: int = 80
    backend_port: int = 8001
    network_name: str = "ragflowauth-network"
    data_dir: str = "/opt/ragflowauth"

    tag: str = ""
    frontend_image: str = ""
    backend_image: str = ""
    temp_dir: Path | None = None
    frontend_tar: Path | None = None
    backend_tar: Path | None = None

