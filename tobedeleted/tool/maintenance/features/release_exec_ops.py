from __future__ import annotations

import subprocess

from tool.maintenance.core.ssh_executor import SSHExecutor


def run_local(argv: list[str], *, timeout_s: int) -> tuple[bool, str]:
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    # Strip known noisy lines that can appear on some Windows OpenSSH builds.
    out = "\n".join(
        line
        for line in out.splitlines()
        if not line.startswith("close - IO is still pending on closed socket.")
    )
    return (proc.returncode == 0), out.strip()


def ssh_cmd(*, ip: str, user: str, command: str, timeout_seconds: int) -> tuple[bool, str]:
    ssh = SSHExecutor(ip, user)
    return ssh.execute(command, timeout_seconds=timeout_seconds)
