from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

DEFAULT_RAGFLOW_BASE_URL = "http://localhost:9380"
_PLACEHOLDER_API_KEYS: set[str] = {"YOUR_RAGFLOW_API_KEY_HERE", "your_api_key_here"}


def default_ragflow_config_path() -> Path:
    # backend/services -> backend -> repo root
    return Path(__file__).resolve().parents[2] / "ragflow_config.json"


def load_ragflow_config(path: Path, *, logger: logging.Logger | None = None) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # JSONDecodeError, permission errors, etc.
        if logger:
            logger.warning(f"Failed to load ragflow config from {path}: {exc}")
        return {}


def is_placeholder_api_key(api_key: str) -> bool:
    value = (api_key or "").strip()
    return (not value) or (value in _PLACEHOLDER_API_KEYS)

