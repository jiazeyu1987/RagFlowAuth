from __future__ import annotations

import os
import subprocess
import time

from .logging_setup import log_to_file


def common_ssh_options() -> list[str]:
    options = [
        "-o",
        "BatchMode=yes",
        "-o",
        "NumberOfPasswordPrompts=0",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ControlMaster=no",
    ]
    if os.name == "nt":
        options = ["-F", "NUL"] + options + [
            "-o",
            "UserKnownHostsFile=NUL",
            "-o",
            "GlobalKnownHostsFile=NUL",
        ]
    else:
        options = options + [
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "GlobalKnownHostsFile=/dev/null",
        ]
    return options


def build_ssh_argv(*, user: str, ip: str, command: str) -> list[str]:
    return ["ssh", *common_ssh_options(), f"{user}@{ip}", command]


def build_scp_argv(*args: str, through_local: bool = False) -> list[str]:
    argv = ["scp", *common_ssh_options()]
    if through_local:
        argv.append("-3")
    argv.extend(args)
    return argv


class SSHExecutor:
    def __init__(self, ip: str, user: str):
        self.ip = ip
        self.user = user

    @staticmethod
    def _strip_known_noise(output: str) -> str:
        """
        Some Windows OpenSSH builds intermittently emit noisy lines like:
        "close - IO is still pending on closed socket."

        Keep logs readable and avoid breaking output parsers (E2E marker parsing).
        """
        if not output:
            return ""
        noise_prefixes = (
            "Warning: Permanently added '",
            "close - IO is still pending on closed socket.",
        )
        lines = [line for line in output.splitlines() if not line.startswith(noise_prefixes)]
        return "\n".join(lines)

    def execute(self, command: str, callback=None, timeout_seconds: int = 310, *, stdin_data=None):
        """
        Execute a command over SSH.

        Important: use argv list (NOT shell=True) to avoid Windows cmd.exe quote/escape issues
        for nested quotes (e.g. docker exec python -c "...").
        """
        ssh_argv = build_ssh_argv(user=self.user, ip=self.ip, command=command)

        log_to_file(f"[SSH] Execute: {command}", "DEBUG")

        # IMPORTANT: In a GUI process, inheriting stdin can cause SSH to hang waiting for
        # interactive prompts (host key verification / password) that will never be answered.
        # Use DEVNULL by default so SSH fails fast with a clear error instead of timing out.
        stdin = subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL

        process = subprocess.Popen(
            ssh_argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=stdin,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        try:
            stdout, stderr = process.communicate(input=stdin_data, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return False, f"Command timed out after {timeout_seconds} seconds"

        output = self._strip_known_noise((stdout or "") + (stderr or ""))
        if callback:
            try:
                callback(output)
            except Exception:
                pass

        if process.returncode == 0:
            return True, output.strip()
        return False, output.strip()

    def execute_with_retry(self, command: str, max_retries: int = 3, callback=None, timeout_seconds: int = 30):
        last_error = ""
        for attempt in range(1, max_retries + 1):
            ok, out = self.execute(command, callback=callback, timeout_seconds=timeout_seconds)
            if ok:
                return True, out
            last_error = out
            if attempt < max_retries:
                time.sleep(1)
        log_to_file(f"[SSH] All retries failed. Last error: {last_error}", "ERROR")
        return False, last_error
