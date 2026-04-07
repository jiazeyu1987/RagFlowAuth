from __future__ import annotations

from dataclasses import dataclass

from tool.maintenance.core.ssh_executor import SSHExecutor
from tool.maintenance.core.service_controller import ServiceController


@dataclass(frozen=True)
class RestartServicesResult:
    ok: bool
    log: str


def restart_ragflow_and_ragflowauth(*, server_ip: str, server_user: str = "root") -> RestartServicesResult:
    """
    Restart RagflowAuth (backend/frontend) and RAGFlow-related containers on the target server.

    Notes:
    - Best-effort for containers that do not exist.
    - Prefer docker compose restart when /opt/ragflowauth/ragflow_compose has a compose file.
    - Does NOT touch unrelated containers like node-exporter/portainer.
    """
    ssh = SSHExecutor(server_ip, server_user)
    logs: list[str] = []

    def run(cmd: str, *, timeout: int = 300) -> tuple[bool, str]:
        ok, out = ssh.execute(cmd, timeout_seconds=timeout)
        logs.append(f"$ {cmd}\n{(out or '').strip()}\n")
        return ok, out or ""

    ok = True
    logs.append(f"[TARGET] {server_user}@{server_ip}")

    # Detect containers (for log visibility only).
    ok1, out = run("docker ps -a --format '{{.Names}}' 2>/dev/null || true", timeout=60)
    names = [line.strip() for line in out.splitlines() if line.strip()]
    ragflowauth = [n for n in names if n in ("ragflowauth-backend", "ragflowauth-frontend")]
    ragflow = [n for n in names if n.startswith("ragflow_compose-")]
    logs.append(f"[DETECT] ragflowauth={ragflowauth if ragflowauth else 'NONE'}")
    logs.append(f"[DETECT] ragflow_compose_containers={len(ragflow)}")

    controller = ServiceController(exec_fn=lambda c, t: ssh.execute(c, timeout_seconds=t), log=None)
    controller.restart_best_effort(app_dir="/opt/ragflowauth")

    # Quick health checks (best-effort)
    _, be_out = run("curl -fsS http://127.0.0.1:8001/health 2>&1 | head -n 2 || true", timeout=30)
    _, rg_out = run("curl -fsS http://127.0.0.1:9380/health 2>&1 | head -n 2 || true", timeout=30)

    # If health checks fail, collect diagnostics to help locate the issue quickly.
    if ("OK" not in (be_out or "")) or ("OK" not in (rg_out or "")):
        logs.append("[DIAG] docker ps -a (ragflowauth + ragflow_compose top)")
        run(
            "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' "
            "| grep -E '^(ragflowauth-|ragflow_compose-)' 2>&1 | sed -n '1,120p' || true",
            timeout=60,
        )

    ok = ok and ok1
    return RestartServicesResult(ok=bool(ok), log="\n".join(logs).strip() + "\n")
