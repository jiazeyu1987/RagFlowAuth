from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ragflow_config import (
    DEFAULT_RAGFLOW_BASE_URL,
    default_ragflow_config_path,
    effective_api_key,
    format_api_key_for_log,
    load_ragflow_config,
    mask_api_key,
)
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
    ui_log = logging.getLogger("uvicorn.error")
    path = Path(config_path) if config_path is not None else default_ragflow_config_path()
    config = load_ragflow_config(path, logger=log)
    base_url = str(config.get("base_url", DEFAULT_RAGFLOW_BASE_URL) or DEFAULT_RAGFLOW_BASE_URL)
    configured_api_key = str(config.get("api_key", "") or "")
    api_key = effective_api_key(base_url=base_url, configured_api_key=configured_api_key)
    config["base_url"] = base_url
    config["api_key"] = api_key
    try:
        source = "configured"
        if ("127.0.0.1" in (base_url or "")) or ("localhost" in (base_url or "")):
            if configured_api_key.strip() != api_key:
                source = "local_default"
        ui_log.warning(
            "RAGFlow config loaded: path=%s base_url=%s api_key=%s",
            str(path),
            base_url,
            f"{format_api_key_for_log(api_key)} ({source})",
        )
    except Exception:
        pass
    http = RagflowHttpClient(
        RagflowHttpClientConfig(
            base_url=base_url,
            api_key=api_key,
            timeout_s=float(config.get("timeout", 10) or 10),
        ),
        logger=log,
    )
    return RagflowConnection(config_path=path, config=config, http=http)
