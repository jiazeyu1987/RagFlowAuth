from __future__ import annotations

from dataclasses import dataclass

from tool.maintenance.core.ssh_executor import SSHExecutor
from tool.maintenance.core.service_controller import ServiceController


@dataclass(frozen=True)
class StopServicesResult:
    ok: bool
    log: str


def stop_ragflow_and_ragflowauth(*, server_ip: str, server_user: str = "root") -> StopServicesResult:
    """
    Stop RagflowAuth (backend/frontend) and RAGFlow-related containers on the target server.

    Design:
    - Stops containers prefixed with `ragflow_compose-` and the two RagflowAuth containers.
    - Does NOT stop unrelated containers like node-exporter/portainer.
    - If compose exists under /opt/ragflowauth/ragflow_compose, prefer `docker compose stop`.
    """
    ssh = SSHExecutor(server_ip, server_user)
    logs: list[str] = []

    def run(cmd: str, *, timeout: int = 300) -> tuple[bool, str]:
        ok, out = ssh.execute(cmd, timeout_seconds=timeout)
        logs.append(f"$ {cmd}\n{(out or '').strip()}\n")
        return ok, out or ""

    ok = True
    logs.append(f"[TARGET] {server_user}@{server_ip}")

    ok1, out = run("docker ps -a --format '{{.Names}}' 2>/dev/null || true", timeout=60)
    names = [line.strip() for line in out.splitlines() if line.strip()]
    ragflowauth = [n for n in names if n in ("ragflowauth-backend", "ragflowauth-frontend")]
    ragflow = [n for n in names if n.startswith("ragflow_compose-")]

    logs.append(f"[DETECT] ragflowauth={ragflowauth if ragflowauth else 'NONE'}")
    logs.append(f"[DETECT] ragflow_compose_containers={len(ragflow)}")

    controller = ServiceController(exec_fn=lambda c, t: ssh.execute(c, timeout_seconds=t), log=None)
    controller.stop_ragflow_stack(app_dir="/opt/ragflowauth", mode="stop")
    controller.stop_ragflowauth()

    run(
        "docker ps -a --format '{{.Names}}\\t{{.Status}}' "
        "| grep -E '^(ragflowauth-|ragflow_compose-)' 2>&1 | sed -n '1,120p' || true",
        timeout=60,
    )

    ok = ok and ok1
    return StopServicesResult(ok=bool(ok), log="\n".join(logs).strip() + "\n")
