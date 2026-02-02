from __future__ import annotations

from dataclasses import dataclass

from tool.maintenance.core.ssh_executor import SSHExecutor


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

    compose_dir = "/opt/ragflowauth/ragflow_compose"
    _, compose_yml = run(
        f"test -f {compose_dir}/docker-compose.yml && echo {compose_dir}/docker-compose.yml || "
        f"(test -f {compose_dir}/docker-compose.yaml && echo {compose_dir}/docker-compose.yaml || echo '')",
        timeout=20,
    )
    compose_lines = (compose_yml or "").strip().splitlines()
    compose_path = compose_lines[-1].strip() if compose_lines else ""

    if compose_path:
        logs.append(f"[RAGFLOW] compose found: {compose_path} -> docker compose stop")
        ok2, _ = run(f"cd {compose_dir} && docker compose stop 2>&1 || true", timeout=600)
        run(f"cd {compose_dir} && docker compose ps 2>&1 | sed -n '1,120p' || true", timeout=60)
        ok = ok and ok1 and ok2
    else:
        if ragflow:
            joined = " ".join(ragflow)
            logs.append(f"[RAGFLOW] compose not found; docker stop {joined}")
            ok2, _ = run(f"docker stop {joined} 2>&1 || true", timeout=600)
            ok = ok and ok1 and ok2
        else:
            logs.append("[RAGFLOW] no ragflow_compose-* containers found; skip")
            ok = ok and ok1

    if ragflowauth:
        joined = " ".join(ragflowauth)
        logs.append(f"[RAGFLOWAUTH] docker stop {joined}")
        ok3, _ = run(f"docker stop {joined} 2>&1 || true", timeout=300)
        ok = ok and ok3
    else:
        logs.append("[RAGFLOWAUTH] ragflowauth-backend/frontend not found; skip")

    run(
        "docker ps -a --format '{{.Names}}\\t{{.Status}}' "
        "| grep -E '^(ragflowauth-|ragflow_compose-)' 2>&1 | sed -n '1,120p' || true",
        timeout=60,
    )

    return StopServicesResult(ok=bool(ok), log="\n".join(logs).strip() + "\n")

