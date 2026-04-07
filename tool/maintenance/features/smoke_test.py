from __future__ import annotations

from dataclasses import dataclass

from tool.maintenance.core.constants import DEFAULT_SERVER_USER
from tool.maintenance.core.ssh_executor import SSHExecutor


@dataclass(frozen=True)
class SmokeStepResult:
    name: str
    ok: bool
    command: str
    output: str


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    report: str
    steps: list[SmokeStepResult]


def feature_run_smoke_test(
    *,
    server_ip: str,
    server_user: str = DEFAULT_SERVER_USER,
    timeout_s: int = 45,
) -> SmokeResult:
    """
    Run a read-only smoke test against a server.

    This is intentionally conservative (no destructive operations).
    """
    ssh = SSHExecutor(server_ip, server_user)

    checks: list[tuple[str, str, bool]] = [
        ("docker", "docker --version 2>&1", True),
        ("containers", "docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' 2>&1", True),
        ("backend_health", "curl -fsS http://127.0.0.1:8001/health 2>&1", True),
        ("frontend_http", "curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ 2>&1 || true", False),
        ("ragflow_http", "curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:9380/ 2>&1 || true", False),
        (
            "replica_mount",
            "mount | grep -E '/mnt/replica' 2>&1 || true; echo '---'; df -h /mnt/replica 2>&1 || true",
            False,
        ),
        ("disk", "df -h /opt/ragflowauth 2>&1 || df -h 2>&1", False),
    ]

    steps: list[SmokeStepResult] = []
    hard_fail = False

    for name, cmd, required in checks:
        ok, out = ssh.execute(cmd, timeout_seconds=timeout_s)
        text = (out or "").strip()
        if name in ("frontend_http", "ragflow_http"):
            # curl -w prints code; allow common "up" codes.
            code = text.splitlines()[-1].strip() if text else ""
            ok = code in {"200", "301", "302"}
        if name == "replica_mount":
            ok = " /mnt/replica" in text or "type cifs" in text or "Filesystem" in text

        steps.append(SmokeStepResult(name=name, ok=ok, command=cmd, output=text))
        if required and not ok:
            hard_fail = True

    lines: list[str] = []
    lines.append(f"SMOKE server={server_ip}")
    for s in steps:
        tag = "OK" if s.ok else "FAIL"
        lines.append(f"[{tag}] {s.name}")
        lines.append(f"  cmd: {s.command}")
        if s.output:
            preview = s.output if len(s.output) <= 800 else (s.output[:800] + " ...<truncated>")
            for ln in preview.splitlines():
                lines.append(f"  out: {ln}")
        lines.append("")

    ok_all = not hard_fail
    lines.append("RESULT: " + ("PASS" if ok_all else "FAIL"))
    return SmokeResult(ok=ok_all, report="\n".join(lines).rstrip(), steps=steps)

