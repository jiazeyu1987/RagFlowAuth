from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tool.maintenance.core.constants import (
    LOCAL_RAGFLOW_BASE_URL,
    PROD_RAGFLOW_BASE_URL,
    PROD_SERVER_IP,
    TEST_RAGFLOW_BASE_URL,
    TEST_SERVER_IP,
    TOOL_DIR,
)
from tool.maintenance.core.ssh_executor import SSHExecutor


REPO_ROOT = TOOL_DIR.parents[1]
LOCAL_RAGFLOW_CONFIG_PATH = REPO_ROOT / "ragflow_config.json"
DEFAULT_REMOTE_APP_DIR = "/opt/ragflowauth"


@dataclass(frozen=True)
class BaseUrlFixResult:
    ok: bool
    before: str
    after: str
    changed: bool
    error: str = ""


def desired_base_url_for_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role == "local":
        return LOCAL_RAGFLOW_BASE_URL
    if role == "test":
        return TEST_RAGFLOW_BASE_URL
    if role == "prod":
        return PROD_RAGFLOW_BASE_URL
    raise ValueError(f"unknown role: {role!r}")


def server_ip_for_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role == "test":
        return TEST_SERVER_IP
    if role == "prod":
        return PROD_SERVER_IP
    raise ValueError(f"unknown remote role: {role!r}")


def _parse_local_base_url(text: str) -> str:
    try:
        obj = json.loads(text)
        val = str(obj.get("base_url", "")).strip()
        return val
    except Exception:
        m = re.search(r'"base_url"\s*:\s*"([^"]+)"', text)
        return (m.group(1).strip() if m else "")


def read_local_base_url(path: Path = LOCAL_RAGFLOW_CONFIG_PATH) -> tuple[bool, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"read failed: {e}"
    base_url = _parse_local_base_url(text)
    if not base_url:
        return False, "base_url not found"
    return True, base_url


def ensure_local_base_url(
    *,
    desired: str = LOCAL_RAGFLOW_BASE_URL,
    path: Path = LOCAL_RAGFLOW_CONFIG_PATH,
) -> BaseUrlFixResult:
    ok, before_or_err = read_local_base_url(path)
    if not ok:
        return BaseUrlFixResult(ok=False, before="", after="", changed=False, error=str(before_or_err))

    before = before_or_err.strip()
    desired = (desired or "").strip()
    if desired and desired in before:
        return BaseUrlFixResult(ok=True, before=before, after=before, changed=False)

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["base_url"] = desired
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        # Fallback to regex replace (preserve formatting best-effort).
        try:
            raw = path.read_text(encoding="utf-8")
            new = re.sub(
                r'("base_url"\s*:\s*")([^"]+)(")',
                rf"\1{desired}\3",
                raw,
                count=1,
            )
            if new == raw:
                return BaseUrlFixResult(
                    ok=False, before=before, after=before, changed=False, error="unable to rewrite base_url"
                )
            path.write_text(new, encoding="utf-8")
        except Exception as e:
            return BaseUrlFixResult(ok=False, before=before, after=before, changed=False, error=str(e))

    ok2, after_or_err = read_local_base_url(path)
    if not ok2:
        return BaseUrlFixResult(ok=False, before=before, after="", changed=True, error=str(after_or_err))
    after = after_or_err.strip()
    return BaseUrlFixResult(ok=True, before=before, after=after, changed=(before != after))


def read_remote_base_url(
    *,
    server_ip: str,
    user: str = "root",
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    timeout_seconds: int = 20,
) -> tuple[bool, str]:
    cfg_path = f"{app_dir}/ragflow_config.json"
    cmd = (
        f"test -f {cfg_path} || (echo MISSING && exit 0); "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    ok, out = SSHExecutor(server_ip, user).execute(cmd, timeout_seconds=timeout_seconds)
    text = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    if not ok:
        return False, (out or "").strip()
    if text == "MISSING":
        return False, f"missing {cfg_path}"
    if not text:
        return False, f"unable to parse base_url from {cfg_path}"
    return True, text


def ensure_remote_base_url(
    *,
    server_ip: str,
    desired: str,
    log: Callable[[str], None] | None = None,
    role_name: str = "",
    user: str = "root",
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
) -> BaseUrlFixResult:
    ok, before_or_err = read_remote_base_url(server_ip=server_ip, user=user, app_dir=app_dir, timeout_seconds=900)
    if not ok:
        return BaseUrlFixResult(ok=False, before="", after="", changed=False, error=str(before_or_err))

    before = before_or_err.strip()
    desired = (desired or "").strip()
    if log:
        prefix = f"[{role_name}] " if role_name else ""
        log(f"{prefix}ragflow base_url: {before}")

    if desired and desired in before:
        return BaseUrlFixResult(ok=True, before=before, after=before, changed=False)

    cfg_path = f"{app_dir}/ragflow_config.json"
    if log:
        prefix = f"[{role_name}] " if role_name else ""
        log(f"{prefix}Fix ragflow base_url -> {desired}")

    fix_cmd = (
        f"set -e; "
        f"cp -f {cfg_path} {cfg_path}.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true; "
        f"tmp=$(mktemp); "
        f"sed -E 's#(\"base_url\"[[:space:]]*:[[:space:]]*\")([^\\\"]+)(\")#\\1{desired}\\3#' {cfg_path} > $tmp; "
        f"mv -f $tmp {cfg_path}; "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    ok2, out2 = SSHExecutor(server_ip, user).execute(fix_cmd, timeout_seconds=900)
    after = (out2 or "").strip().splitlines()[-1].strip() if (out2 or "").strip() else ""
    if (not ok2) or (desired not in after):
        return BaseUrlFixResult(ok=False, before=before, after=after, changed=True, error=(out2 or "").strip())

    if log:
        prefix = f"[{role_name}] " if role_name else ""
        log(f"{prefix}ragflow base_url updated: {after}")
    return BaseUrlFixResult(ok=True, before=before, after=after, changed=True)
