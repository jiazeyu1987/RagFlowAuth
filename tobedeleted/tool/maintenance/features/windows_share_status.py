from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tool.maintenance.core.constants import DEFAULT_WINDOWS_SHARE_HOST, SCRIPTS_DIR


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


def check_mount_status(*, server_host: str, server_user: str, scripts_dir: Path = SCRIPTS_DIR) -> PowerShellRunResult:
    script_path = scripts_dir / "check-mount-status.ps1"
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
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )

    log_content = _read_temp_log("check_mount_status.log")
    return PowerShellRunResult(
        ok=(result.returncode == 0),
        returncode=result.returncode,
        log_content=log_content,
        stderr=(result.stderr or ""),
    )

