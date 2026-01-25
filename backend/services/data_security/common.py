from __future__ import annotations

import subprocess
import time
from pathlib import Path


def timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, shell=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()

