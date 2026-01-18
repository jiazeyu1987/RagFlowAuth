from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ragflow_config import DEFAULT_RAGFLOW_BASE_URL, default_ragflow_config_path, load_ragflow_config
from .ragflow_http_client import RagflowHttpClient, RagflowHttpClientConfig


@dataclass(frozen=True)
class RagflowConnection:
    config_path: Path
    config: dict[str, Any]
    http: RagflowHttpClient


def create_ragflow_connection(
    *,
    config_path: str | Path | None = None,
    logger: logging.Logger | None = None,
) -> RagflowConnection:
    log = logger or logging.getLogger(__name__)
    path = Path(config_path) if config_path is not None else default_ragflow_config_path()
    config = load_ragflow_config(path, logger=log)
    http = RagflowHttpClient(
        RagflowHttpClientConfig(
            base_url=config.get("base_url", DEFAULT_RAGFLOW_BASE_URL),
            api_key=config.get("api_key", ""),
            timeout_s=float(config.get("timeout", 10) or 10),
        ),
        logger=log,
    )
    return RagflowConnection(config_path=path, config=config, http=http)
