from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeployOnlyOfficePipelineArtifacts:
    tmp_dir: Path | None = None
    tar_local: Path | None = None
    tar_remote: str = ""


@dataclass(frozen=True)
class DeployOnlyOfficeBackendContext:
    backend_inspect: dict
    backend_image: str
    onlyoffice_jwt_secret: str
    file_token_secret: str
    onlyoffice_server_url: str
    onlyoffice_api_base: str
