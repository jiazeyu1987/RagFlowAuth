from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.app.core.paths import repo_root

DEFAULT_RAGFLOW_BASE_URL = "http://localhost:9380"
_PLACEHOLDER_API_KEYS: set[str] = {"YOUR_RAGFLOW_API_KEY_HERE", "your_api_key_here"}


def default_ragflow_config_path() -> Path:
    return repo_root() / "ragflow_config.json"


def _looks_mojibake(text: str) -> bool:
    # Heuristic: contains many latin-1 supplement chars (common mojibake symptom)
    return any("\u00c0" <= ch <= "\u00ff" for ch in text)


def _contains_cjk(text: str) -> bool:
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


def _maybe_fix_mojibake(text: str) -> str:
    """
    Best-effort fix for strings that are actually UTF-8 bytes interpreted as latin-1.

    Example: '\\xe5\\xb1\\x95...' (as characters) -> '展...'
    """
    if not isinstance(text, str) or not text or not _looks_mojibake(text):
        return text

    try:
        candidate = text.encode("latin-1").decode("utf-8")
    except Exception:
        return text

    # Only accept the fix when it meaningfully improves readability (CJK appears).
    if _contains_cjk(candidate):
        return candidate
    return text


def _repair_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return _maybe_fix_mojibake(obj)
    if isinstance(obj, list):
        return [_repair_obj(x) for x in obj]
    if isinstance(obj, dict):
        repaired: dict[Any, Any] = {}
        for k, v in obj.items():
            new_k = _maybe_fix_mojibake(k) if isinstance(k, str) else k
            repaired[new_k] = _repair_obj(v)
        return repaired
    return obj


def load_ragflow_config(path: Path, *, logger: logging.Logger | None = None) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return _repair_obj(data)
    except FileNotFoundError:
        return {}
    except Exception as exc:  # JSONDecodeError, permission errors, etc.
        if logger:
            logger.warning(f"Failed to load ragflow config from {path}: {exc}")
        return {}


def is_placeholder_api_key(api_key: str) -> bool:
    value = (api_key or "").strip()
    return (not value) or (value in _PLACEHOLDER_API_KEYS)
