from __future__ import annotations

from dataclasses import dataclass

from tool.maintenance.core.ssh_executor import SSHExecutor


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

    # Detect containers
    ok1, out = run("docker ps -a --format '{{.Names}}' 2>/dev/null || true", timeout=60)
    names = [line.strip() for line in out.splitlines() if line.strip()]
    ragflowauth = [n for n in names if n in ("ragflowauth-backend", "ragflowauth-frontend")]
    ragflow = [n for n in names if n.startswith("ragflow_compose-")]

    logs.append(f"[DETECT] ragflowauth={ragflowauth if ragflowauth else 'NONE'}")
    logs.append(f"[DETECT] ragflow_compose_containers={len(ragflow)}")

    # Restart ragflow compose stack if compose file exists.
    compose_dir = "/opt/ragflowauth/ragflow_compose"
    ok2, compose_yml = run(
        f"test -f {compose_dir}/docker-compose.yml && echo {compose_dir}/docker-compose.yml || "
        f"(test -f {compose_dir}/docker-compose.yaml && echo {compose_dir}/docker-compose.yaml || echo '')",
        timeout=20,
    )
    compose_lines = (compose_yml or "").strip().splitlines()
    compose_path = compose_lines[-1].strip() if compose_lines else ""

    if compose_path:
        logs.append(f"[RAGFLOW] compose found: {compose_path} -> docker compose restart")
        ok3, _ = run(f"cd {compose_dir} && docker compose restart 2>&1 || true", timeout=600)
        # Ensure services are actually up (restart is a no-op if nothing is running).
        logs.append("[RAGFLOW] ensure up: docker compose up -d")
        ok3b, _ = run(f"cd {compose_dir} && docker compose up -d 2>&1 || true", timeout=900)
        run(f"cd {compose_dir} && docker compose ps 2>&1 | sed -n '1,120p' || true", timeout=60)
        ok = ok and ok1 and ok2 and ok3 and ok3b
    else:
        if ragflow:
            joined = " ".join(ragflow)
            logs.append(f"[RAGFLOW] compose not found; docker restart {joined}")
            ok3, _ = run(f"docker restart {joined} 2>&1 || true", timeout=600)
            ok = ok and ok1 and ok2 and ok3
        else:
            logs.append("[RAGFLOW] no ragflow_compose-* containers found; skip")
            ok = ok and ok1 and ok2

    # Restart RagflowAuth containers.
    if ragflowauth:
        joined = " ".join(ragflowauth)
        logs.append(f"[RAGFLOWAUTH] docker restart {joined}")
        ok4, _ = run(f"docker restart {joined} 2>&1 || true", timeout=300)
        ok = ok and ok4
    else:
        logs.append("[RAGFLOWAUTH] ragflowauth-backend/frontend not found; skip")

    # Quick health checks (best-effort)
    ok_be, be_out = run("curl -fsS http://127.0.0.1:8001/health 2>&1 | head -n 2 || true", timeout=30)
    ok_rg, rg_out = run("curl -fsS http://127.0.0.1:9380/health 2>&1 | head -n 2 || true", timeout=30)

    # If health checks fail, collect diagnostics to help locate the issue quickly.
    if (ragflowauth and ("OK" not in (be_out or ""))) or (compose_path and ("OK" not in (rg_out or ""))):
        logs.append("[DIAG] docker ps -a (ragflowauth + ragflow_compose top)")
        run(
            "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' "
            "| grep -E '^(ragflowauth-|ragflow_compose-)' 2>&1 | sed -n '1,120p' || true",
            timeout=60,
        )

    if ragflowauth and "OK" not in (be_out or ""):
        logs.append("[DIAG] ragflowauth-backend inspect + logs (tail)")
        run("docker inspect -f '{{.State.Status}} exit={{.State.ExitCode}} started={{.State.StartedAt}}' ragflowauth-backend 2>&1 || true", timeout=30)
        run("docker logs --tail 120 ragflowauth-backend 2>&1 || true", timeout=60)

    if compose_path and "OK" not in (rg_out or ""):
        logs.append("[DIAG] ragflow compose ps/logs (tail)")
        run(f"cd {compose_dir} && docker compose ps 2>&1 | sed -n '1,200p' || true", timeout=60)
        run(f"cd {compose_dir} && docker compose logs --tail 80 2>&1 || true", timeout=120)

    return RestartServicesResult(ok=bool(ok), log="\n".join(logs).strip() + "\n")
