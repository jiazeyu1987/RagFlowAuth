from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from backend.app.core.paths import repo_root

DEFAULT_RAGFLOW_BASE_URL = "http://localhost:9380"
_PLACEHOLDER_API_KEYS: set[str] = {"YOUR_RAGFLOW_API_KEY_HERE", "your_api_key_here"}
# Local/dev convenience: when base_url points to a local RAGFlow, force a fixed API key so
# changing base_url doesn't require re-configuring api_key in every environment.
LOCAL_RAGFLOW_API_KEY = "ragflow-VmYjRmNjIwZjc2MzExZjBhZmMyMDI0Mm"

def mask_api_key(api_key: str) -> str:
    v = (api_key or "").strip()
    if not v:
        return "(empty)"
    if len(v) <= 8:
        return "***"
    return f"{v[:6]}…{v[-4:]}"


def format_api_key_for_log(api_key: str) -> str:
    """
    Never print secrets by default.

    If you *really* need to see the full API key locally for debugging, set:
      RAGFLOWAUTH_LOG_SECRETS=1
    """
    if os.environ.get("RAGFLOWAUTH_LOG_SECRETS", "").strip() == "1":
        return (api_key or "").strip() or "(empty)"
    return mask_api_key(api_key)


def is_local_base_url(base_url: str) -> bool:
    v = (base_url or "").strip().lower()
    return ("127.0.0.1" in v) or ("localhost" in v)


def effective_api_key(*, base_url: str, configured_api_key: str) -> str:
    """
    Decide the effective API key:
    - Local base_url: prefer configured api_key (if set and not placeholder), else fall back to LOCAL_RAGFLOW_API_KEY.
    - Non-local base_url: use configured api_key as-is.
    """
    if is_local_base_url(base_url):
        if not is_placeholder_api_key(configured_api_key):
            return (configured_api_key or "").strip()
        return LOCAL_RAGFLOW_API_KEY
    return configured_api_key or ""


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
