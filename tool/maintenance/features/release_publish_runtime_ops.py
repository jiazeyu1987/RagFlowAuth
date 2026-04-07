from __future__ import annotations

import time
from typing import Callable

DEFAULT_UVICORN_WORKERS = "2"


def sh_single_quote(value: str) -> str:
    # Wrap in single quotes, escape any embedded single quote.
    # abc'd -> 'abc'"'"'d'
    return "'" + value.replace("'", "'\"'\"'") + "'"


def ensure_network(*, ssh_cmd: Callable[[str, str], tuple[bool, str]], ip: str, network_name: str) -> tuple[bool, str]:
    if not network_name or network_name in ("default", "host", "bridge", "none"):
        return True, ""
    return ssh_cmd(ip, f"docker network inspect {network_name} >/dev/null 2>&1 || docker network create {network_name}")


def build_recreate_from_inspect(
    container_name: str,
    inspect: dict,
    *,
    new_image: str,
    sh_single_quote_fn: Callable[[str], str] = sh_single_quote,
) -> str:
    """
    Build a docker run command based on an existing container's inspect output,
    keeping binds/ports/env/network/restart, but swapping the image.
    """
    host_cfg = inspect.get("HostConfig") or {}
    cfg = inspect.get("Config") or {}

    parts: list[str] = ["docker", "run", "-d", "--name", container_name]

    network_mode = str(host_cfg.get("NetworkMode") or "").strip()
    if network_mode and network_mode not in ("default", "bridge"):
        # for named networks, docker run uses --network <name>
        if network_mode not in ("host", "none"):
            parts += ["--network", network_mode]
        else:
            parts += ["--network", network_mode]

    restart = (host_cfg.get("RestartPolicy") or {}).get("Name") or ""
    if restart:
        parts += ["--restart", str(restart)]

    port_bindings = host_cfg.get("PortBindings") or {}
    if isinstance(port_bindings, dict):
        for container_port, bindings in port_bindings.items():
            if not isinstance(bindings, list):
                continue
            cport = str(container_port).split("/")[0]
            for binding in bindings:
                if not isinstance(binding, dict):
                    continue
                host_port = str(binding.get("HostPort") or "").strip()
                if host_port:
                    parts += ["-p", f"{host_port}:{cport}"]

    binds = host_cfg.get("Binds") or []
    if isinstance(binds, list):
        for bind in binds:
            if isinstance(bind, str) and bind.strip():
                parts += ["-v", bind.strip()]

    envs = cfg.get("Env") or []
    has_uvicorn_workers = False
    enforce_uvicorn_workers_default = container_name == "ragflowauth-backend"
    if isinstance(envs, list):
        for env in envs:
            if not (isinstance(env, str) and env and "=" in env):
                continue
            key, value = env.split("=", 1)
            if enforce_uvicorn_workers_default and key == "UVICORN_WORKERS":
                resolved = value.strip() or DEFAULT_UVICORN_WORKERS
                parts += ["-e", f"UVICORN_WORKERS={resolved}"]
                has_uvicorn_workers = True
                continue
            parts += ["-e", env]
    if enforce_uvicorn_workers_default and not has_uvicorn_workers:
        parts += ["-e", f"UVICORN_WORKERS={DEFAULT_UVICORN_WORKERS}"]

    cmd = " ".join(
        sh_single_quote_fn(p) if any(ch in p for ch in (" ", "\t", "$", "`", "\"", "'")) else p
        for p in parts
    )
    return f"{cmd} {new_image}"


def wait_server_ready(
    *,
    ssh_cmd: Callable[[str, str], tuple[bool, str]],
    prod_ip: str,
    healthcheck_url: str,
    backend_container: str = "ragflowauth-backend",
    timeout_s: int = 90,
) -> tuple[bool, str]:
    """
    Wait for the backend container to be running and /health to respond.
    On failure, include useful diagnostics for quick root-cause analysis.
    """
    started = time.time()
    last_health_out = ""

    while True:
        ok, state = ssh_cmd(prod_ip, f"docker inspect -f '{{{{.State.Status}}}}' {backend_container} 2>/dev/null || echo ''")
        state = (state or "").strip()
        if ok and state == "running":
            ok2, out = ssh_cmd(prod_ip, f"curl -fsS {healthcheck_url} >/dev/null && echo OK")
            if ok2:
                return True, "OK"
            last_health_out = out or ""
        else:
            last_health_out = f"backend container state={state or '(unknown)'}"

        if time.time() - started > timeout_s:
            break
        time.sleep(3)

    # Diagnostics
    diag: list[str] = []
    diag.append("[DIAG] healthcheck did not become ready in time")
    diag.append(f"[DIAG] last_health_out: {last_health_out.strip()}")

    ok, out = ssh_cmd(prod_ip, "docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E 'ragflowauth-' || true")
    if ok:
        diag.append("[DIAG] docker ps -a (ragflowauth-*):")
        diag.append((out or "").strip())

    ok, out = ssh_cmd(prod_ip, f"docker logs --tail 120 {backend_container} 2>&1 || true")
    if ok:
        diag.append("[DIAG] backend logs (tail 120):")
        diag.append((out or "").strip())

    ok, out = ssh_cmd(prod_ip, "docker logs --tail 80 ragflowauth-frontend 2>&1 || true")
    if ok:
        diag.append("[DIAG] frontend logs (tail 80):")
        diag.append((out or "").strip())

    return False, "\n".join([x for x in diag if x])


def recreate_server_containers_from_inspect_impl(
    *,
    server_ip: str,
    backend_image: str,
    frontend_image: str,
    healthcheck_url: str,
    log,
    docker_inspect_fn,
    ssh_cmd,
    ensure_network_fn,
    build_recreate_fn,
    wait_ready_fn,
) -> tuple[bool, str]:
    """
    Recreate ragflowauth-frontend/backend on a server by:
    - inspecting current containers for ports/mounts/env/network/restart policy
    - removing existing containers
    - running new containers with the provided images
    - waiting for healthcheck
    """
    prod_backend = docker_inspect_fn(server_ip, "ragflowauth-backend")
    prod_frontend = docker_inspect_fn(server_ip, "ragflowauth-frontend")
    if not prod_backend or not prod_frontend:
        return False, "containers not found (ragflowauth-backend/frontend)"

    network_mode = str((prod_backend.get("HostConfig") or {}).get("NetworkMode") or "").strip()
    ok, out = ensure_network_fn(server_ip, network_mode)
    if not ok:
        return False, f"ensure network failed: {out}"

    ok, out = ssh_cmd(
        server_ip,
        "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true; "
        "docker rm -f ragflowauth-backend ragflowauth-frontend 2>/dev/null || true",
    )
    if not ok:
        return False, f"stop/rm failed: {out}"

    run_front = build_recreate_fn("ragflowauth-frontend", prod_frontend, new_image=frontend_image)
    run_back = build_recreate_fn("ragflowauth-backend", prod_backend, new_image=backend_image)
    log(f"run frontend: {run_front}")
    ok, out = ssh_cmd(server_ip, run_front)
    if not ok:
        return False, f"run frontend failed: {out}"
    if out:
        log(f"frontend started: {(out or '').strip()}")

    log(f"run backend: {run_back}")
    ok, out = ssh_cmd(server_ip, run_back)
    if not ok:
        return False, f"run backend failed: {out}"
    if out:
        log(f"backend started: {(out or '').strip()}")

    ok, out = wait_ready_fn(prod_ip=server_ip, healthcheck_url=healthcheck_url)
    if not ok:
        return False, f"healthcheck failed:\n{out}"
    return True, "OK"


def bootstrap_server_containers_impl(
    *,
    server_ip: str,
    backend_image: str,
    frontend_image: str,
    healthcheck_url: str,
    log,
    ssh_cmd,
    ensure_network_fn,
    wait_ready_fn,
    app_dir: str,
    network_name: str,
    frontend_port: int,
    backend_port: int,
) -> tuple[bool, str]:
    """
    First-time deployment fallback when target server has no existing containers to inspect.
    """
    log(f"[BOOTSTRAP] No existing containers detected; creating new containers on {server_ip} (docker run mode).")

    # Ensure required directories exist
    ok, out = ssh_cmd(
        server_ip,
        f"mkdir -p {app_dir}/data {app_dir}/uploads {app_dir}/backups {app_dir}/releases /mnt/replica && echo OK",
    )
    if not ok:
        return False, f"mkdir failed: {out}"

    # Validate required config artifacts (minimum required to start backend)
    required_files = [
        f"{app_dir}/ragflow_config.json",
    ]
    required_dirs = [
        f"{app_dir}/ragflow_compose",
    ]

    missing: list[str] = []
    for path in required_files:
        ok, out = ssh_cmd(server_ip, f"test -f {path} && echo OK || echo MISSING")
        if (out or "").strip().endswith("MISSING"):
            missing.append(path)
    for path in required_dirs:
        ok, out = ssh_cmd(server_ip, f"test -d {path} && echo OK || echo MISSING")
        if (out or "").strip().endswith("MISSING"):
            missing.append(path)

    if missing:
        log("[BOOTSTRAP] Missing required files/dirs on target server:")
        for path in missing:
            log(f"[BOOTSTRAP]  - {path}")
        return False, "missing required deployment artifacts under app_dir"

    # Optional backup config (can be absent; backend will use defaults).
    ok, out = ssh_cmd(server_ip, f"test -f {app_dir}/backup_config.json && echo OK || echo ''")
    has_backup_cfg = bool((out or "").strip())
    if not has_backup_cfg:
        log("[BOOTSTRAP] Note: backup_config.json not found; backup will use default target_dir inside container.")

    ok, out = ensure_network_fn(server_ip, network_name)
    if not ok:
        return False, f"ensure network failed: {out}"

    ok, out = ssh_cmd(
        server_ip,
        "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true; "
        "docker rm -f ragflowauth-backend ragflowauth-frontend 2>/dev/null || true",
    )
    if not ok:
        return False, f"stop/rm failed: {out}"

    run_front = (
        "docker run -d "
        "--name ragflowauth-frontend "
        f"--network {network_name} "
        f"-p {frontend_port}:80 "
        "--restart unless-stopped "
        f"{frontend_image}"
    )
    log(f"[BOOTSTRAP] run frontend: {run_front}")
    ok, out = ssh_cmd(server_ip, run_front)
    if not ok:
        return False, f"run frontend failed: {out}"
    if out:
        log(f"[BOOTSTRAP] frontend started: {(out or '').strip()}")

    run_back = (
        "docker run -d "
        "--name ragflowauth-backend "
        f"--network {network_name} "
        f"-p {backend_port}:{backend_port} "
        "-e TZ=Asia/Shanghai "
        "-e HOST=0.0.0.0 "
        f"-e PORT={backend_port} "
        f"-e UVICORN_WORKERS={DEFAULT_UVICORN_WORKERS} "
        "-e DATABASE_PATH=data/auth.db "
        "-e UPLOAD_DIR=data/uploads "
        f"-v {app_dir}/data:/app/data "
        f"-v {app_dir}/uploads:/app/uploads "
        f"-v {app_dir}/ragflow_config.json:/app/ragflow_config.json:ro "
        f"-v {app_dir}/ragflow_compose:/app/ragflow_compose:ro "
        f"-v {app_dir}/backups:/app/data/backups "
        "-v /mnt/replica:/mnt/replica "
        "-v /var/run/docker.sock:/var/run/docker.sock:ro "
        "--restart unless-stopped "
        f"{backend_image}"
    )
    if has_backup_cfg:
        run_back = run_back.replace(
            f"-v {app_dir}/backups:/app/data/backups ",
            f"-v {app_dir}/backup_config.json:/app/backup_config.json:ro -v {app_dir}/backups:/app/data/backups ",
        )
    log(f"[BOOTSTRAP] run backend: {run_back}")
    ok, out = ssh_cmd(server_ip, run_back)
    if not ok:
        return False, f"run backend failed: {out}"
    if out:
        log(f"[BOOTSTRAP] backend started: {(out or '').strip()}")

    ok, out = wait_ready_fn(prod_ip=server_ip, healthcheck_url=healthcheck_url)
    if not ok:
        return False, f"healthcheck failed:\n{out}"
    return True, "OK"
