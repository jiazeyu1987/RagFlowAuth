from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tool.maintenance.core.constants import (
    DEFAULT_WINDOWS_SHARE_HOST,
    DEFAULT_WINDOWS_SHARE_NAME,
    DEFAULT_WINDOWS_SHARE_PASSWORD,
    DEFAULT_WINDOWS_SHARE_USERNAME,
    MOUNT_POINT,
    REPLICA_TARGET_DIR,
    SCRIPTS_DIR,
)


@dataclass(frozen=True)
class PowerShellRunResult:
    ok: bool
    returncode: int
    log_content: str
    stderr: str


def _read_temp_log(filename: str) -> str:
    log_file = Path(tempfile.gettempdir()) / filename
    if not log_file.exists():
        return ""
    try:
        return log_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def mount_windows_share(*, server_host: str, server_user: str, scripts_dir: Path = SCRIPTS_DIR) -> PowerShellRunResult:
    script_path = scripts_dir / "mount-windows-share.ps1"
    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-ServerHost",
            server_host,
            "-ServerUser",
            server_user,
            "-WindowsHost",
            DEFAULT_WINDOWS_SHARE_HOST,
            "-ShareName",
            DEFAULT_WINDOWS_SHARE_NAME,
            "-ShareUsername",
            DEFAULT_WINDOWS_SHARE_USERNAME,
            "-SharePassword",
            DEFAULT_WINDOWS_SHARE_PASSWORD,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )

    log_content = _read_temp_log("mount_windows_share.log")
    # Small invariant to detect accidental script changes.
    if MOUNT_POINT not in log_content and REPLICA_TARGET_DIR not in log_content:
        # Still return the log, but callers can decide how to display.
        pass

    return PowerShellRunResult(
        ok=(result.returncode == 0),
        returncode=result.returncode,
        log_content=log_content,
        stderr=(result.stderr or ""),
    )

