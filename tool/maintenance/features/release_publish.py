from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
import json

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, PROD_SERVER_IP, TEST_SERVER_IP
from tool.maintenance.core.ssh_executor import SSHExecutor


DEFAULT_REMOTE_APP_DIR = "/opt/ragflowauth"


@dataclass(frozen=True)
class ServerVersionInfo:
    server_ip: str
    backend_image: str
    frontend_image: str
    compose_path: str
    env_path: str
    compose_sha256: str
    env_sha256: str


@dataclass(frozen=True)
class PublishResult:
    ok: bool
    log: str
    version_before: ServerVersionInfo | None
    version_after: ServerVersionInfo | None


def _run_local(argv: list[str], *, timeout_s: int = 3600) -> tuple[bool, str]:
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


def _ssh_cmd(ip: str, command: str) -> tuple[bool, str]:
    ssh = SSHExecutor(ip, DEFAULT_SERVER_USER)
    return ssh.execute(command, timeout_seconds=900)


def _read_ragflow_base_url(*, server_ip: str, app_dir: str) -> tuple[bool, str]:
    """
    Read base_url from ragflow_config.json on the target server.
    Uses POSIX tools (sed/head) so it works even when host python isn't installed.
    """
    cfg_path = f"{app_dir}/ragflow_config.json"
    cmd = (
        f"test -f {cfg_path} || (echo MISSING && exit 0); "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    ok, out = _ssh_cmd(server_ip, cmd)
    text = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    if text == "MISSING":
        return False, f"missing {cfg_path}"
    if not ok:
        return False, (out or "").strip()
    if not text:
        return False, f"unable to parse base_url from {cfg_path}"
    return True, text


def preflight_check_ragflow_base_url(
    *,
    server_ip: str,
    expected_server_ip: str,
    app_dir: str,
    log,
    role_name: str,
) -> bool:
    """
    Guardrail: ensure a server's ragflow_config.json points to its own RAGFlow (or localhost),
    so TEST doesn't read PROD and vice versa.
    """
    ok, base_url_or_err = _read_ragflow_base_url(server_ip=server_ip, app_dir=app_dir)
    if not ok:
        log(f"[PRECHECK] [ERROR] {role_name} ragflow_config base_url check failed: {base_url_or_err}")
        log(f"[PRECHECK] Hint: ensure {app_dir}/ragflow_config.json exists on {server_ip}.")
        return False

    base_url = base_url_or_err.strip()
    log(f"[PRECHECK] {role_name} ragflow base_url: {base_url}")

    allowed = (expected_server_ip in base_url) or ("localhost" in base_url) or ("127.0.0.1" in base_url)
    if not allowed:
        log(f"[PRECHECK] [ERROR] {role_name} ragflow_config.json base_url looks wrong.")
        log(f"[PRECHECK] Expected to contain '{expected_server_ip}' (or localhost), got: {base_url}")
        return False
    return True
def docker_load_tar_on_server(*, server_ip: str, tar_path: str) -> tuple[bool, str]:
    """Load a docker image tarball on a remote server."""
    return _ssh_cmd(server_ip, f"docker load -i {tar_path}")


def _docker_label(ip: str, container_name: str, label: str) -> str:
    # Use a single-quoted Go template, and a double-quoted label key inside it.
    # Avoid nesting single quotes (which breaks in /bin/sh).
    template = f'{{{{ index .Config.Labels "{label}" }}}}'
    ok, out = _ssh_cmd(ip, f"docker inspect -f '{template}' {container_name} 2>/dev/null || echo ''")
    if not ok:
        return ""
    text = (out or "").strip()
    if not text:
        return ""
    return text.splitlines()[-1].strip()

def _detect_compose_and_env_paths(ip: str, *, app_dir: str) -> tuple[str, str]:
    """
    Try to detect compose/.env paths from the running containers (Docker Compose labels),
    then fall back to common locations under `app_dir`.
    """
    container = "ragflowauth-backend"
    config_files = _docker_label(ip, container, "com.docker.compose.project.config_files")
    working_dir = _docker_label(ip, container, "com.docker.compose.project.working_dir")

    candidates: list[str] = []
    if config_files:
        for raw in config_files.split(","):
            p = raw.strip()
            if p:
                candidates.append(p)

    candidates.extend(
        [
            f"{app_dir}/docker-compose.yml",
            f"{app_dir}/docker-compose.yaml",
            f"{app_dir}/compose/docker-compose.yml",
            f"{app_dir}/compose/docker-compose.yaml",
        ]
    )

    compose_path = ""
    for p in candidates:
        ok, out = _ssh_cmd(ip, f"test -f {p} && echo FOUND || echo ''")
        if ok and (out or "").strip().endswith("FOUND"):
            compose_path = p
            break

    if not compose_path:
        # Last resort: search common roots for a compose file that references ragflowauth services.
        find_cmd = r"""
set -e
roots="/opt /data /var/lib/docker/volumes"
pattern='docker-compose*.yml docker-compose*.yaml'
for root in $roots; do
  [ -d "$root" ] || continue
  find "$root" -maxdepth 6 -type f \( -name 'docker-compose*.yml' -o -name 'docker-compose*.yaml' \) 2>/dev/null \
    | while IFS= read -r f; do
        if grep -q 'ragflowauth-backend' "$f" 2>/dev/null; then
          echo "$f"
          exit 0
        fi
      done
done
echo ''
""".strip()
        ok, out = _ssh_cmd(ip, find_cmd)
        if ok:
            candidate = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
            if candidate:
                compose_path = candidate

    env_candidates: list[str] = []
    if working_dir:
        env_candidates.append(f"{working_dir.rstrip('/')}/.env")
    if compose_path and "/" in compose_path:
        env_candidates.append(compose_path.rsplit("/", 1)[0] + "/.env")
    env_candidates.append(f"{app_dir}/.env")

    env_path = ""
    for p in env_candidates:
        ok, out = _ssh_cmd(ip, f"test -f {p} && echo FOUND || echo ''")
        if ok and (out or "").strip().endswith("FOUND"):
            env_path = p
            break

    return compose_path, env_path


def _sh_single_quote(value: str) -> str:
    # Wrap in single quotes, escape any embedded single quote.
    # abc'd -> 'abc'"'"'d'
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _docker_inspect(ip: str, container_name: str) -> dict | None:
    ok, out = _ssh_cmd(ip, f"docker inspect {container_name} 2>/dev/null || echo '[]'")
    if not ok:
        return None
    text = (out or "").strip()
    try:
        data = json.loads(text)
    except Exception:
        return None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def _detect_ragflow_images_on_server(*, server_ip: str) -> list[str]:
    """
    Best-effort detection of RAGFlow container images on a server.

    We only need image tags (strings) so we can optionally include them in docker save/load.
    This helps when PROD can't pull from internet (offline) and the local image cache gets deleted/corrupted.
    """
    # Prefer containers created by /opt/ragflowauth/ragflow_compose (commonly named ragflow_compose-*).
    ok, out = _ssh_cmd(
        server_ip,
        "docker ps --format '{{.Names}}\t{{.Image}}' | grep -E '^ragflow_compose-.*ragflow' || true",
    )
    images: list[str] = []
    if ok and out:
        for line in (out or "").splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                img = parts[1].strip()
                if img and img not in images:
                    images.append(img)

    # Fallback: detect common upstream image name if container naming differs.
    if not images:
        ok, out = _ssh_cmd(
            server_ip,
            "docker ps --format '{{.Image}}' | grep -E '^infiniflow/ragflow:' | head -n 5 || true",
        )
        if ok and out:
            for img in (out or "").splitlines():
                img = img.strip()
                if img and img not in images:
                    images.append(img)

    return images


def _ensure_network(ip: str, network_name: str) -> tuple[bool, str]:
    if not network_name or network_name in ("default", "host", "bridge", "none"):
        return True, ""
    return _ssh_cmd(ip, f"docker network inspect {network_name} >/dev/null 2>&1 || docker network create {network_name}")


def _build_recreate_from_inspect(container_name: str, inspect: dict, *, new_image: str) -> str:
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
            for b in bindings:
                if not isinstance(b, dict):
                    continue
                host_port = str(b.get("HostPort") or "").strip()
                if host_port:
                    parts += ["-p", f"{host_port}:{cport}"]

    binds = host_cfg.get("Binds") or []
    if isinstance(binds, list):
        for b in binds:
            if isinstance(b, str) and b.strip():
                parts += ["-v", b.strip()]

    envs = cfg.get("Env") or []
    if isinstance(envs, list):
        for e in envs:
            if isinstance(e, str) and e and "=" in e:
                parts += ["-e", e]

    cmd = " ".join(_sh_single_quote(p) if any(ch in p for ch in (" ", "\t", "$", "`", "\"", "'")) else p for p in parts)
    return f"{cmd} {new_image}"


def _wait_prod_ready(
    *,
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
        ok, state = _ssh_cmd(prod_ip, f"docker inspect -f '{{{{.State.Status}}}}' {backend_container} 2>/dev/null || echo ''")
        state = (state or "").strip()
        if ok and state == "running":
            ok2, out = _ssh_cmd(prod_ip, f"curl -fsS {healthcheck_url} >/dev/null && echo OK")
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

    ok, out = _ssh_cmd(prod_ip, "docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E 'ragflowauth-' || true")
    if ok:
        diag.append("[DIAG] docker ps -a (ragflowauth-*):")
        diag.append((out or "").strip())

    ok, out = _ssh_cmd(prod_ip, f"docker logs --tail 120 {backend_container} 2>&1 || true")
    if ok:
        diag.append("[DIAG] backend logs (tail 120):")
        diag.append((out or "").strip())

    ok, out = _ssh_cmd(prod_ip, "docker logs --tail 80 ragflowauth-frontend 2>&1 || true")
    if ok:
        diag.append("[DIAG] frontend logs (tail 80):")
        diag.append((out or "").strip())

    return False, "\n".join([x for x in diag if x])


def _sha256_of_remote_file(ip: str, path: str) -> str:
    ok, out = _ssh_cmd(ip, f"test -f {path} && sha256sum {path} | awk '{{print $1}}' || echo ''")
    if not ok:
        return ""
    text = (out or "").strip()
    if not text:
        return ""
    return text.splitlines()[-1].strip()


def _docker_container_image(ip: str, container_name: str) -> str:
    ok, out = _ssh_cmd(ip, f"docker inspect -f '{{{{.Config.Image}}}}' {container_name} 2>/dev/null || echo ''")
    if not ok:
        return ""
    text = (out or "").strip()
    if not text:
        return ""
    return text.splitlines()[-1].strip()


def get_server_version_info(*, server_ip: str, app_dir: str = DEFAULT_REMOTE_APP_DIR) -> ServerVersionInfo:
    backend_image = _docker_container_image(server_ip, "ragflowauth-backend")
    frontend_image = _docker_container_image(server_ip, "ragflowauth-frontend")
    compose_path, env_path = _detect_compose_and_env_paths(server_ip, app_dir=app_dir)
    compose_sha256 = _sha256_of_remote_file(server_ip, compose_path) if compose_path else ""
    env_sha256 = _sha256_of_remote_file(server_ip, env_path) if env_path else ""
    return ServerVersionInfo(
        server_ip=server_ip,
        backend_image=backend_image,
        frontend_image=frontend_image,
        compose_path=compose_path,
        env_path=env_path,
        compose_sha256=compose_sha256,
        env_sha256=env_sha256,
    )


def publish_from_test_to_prod(
    *,
    version: str | None = None,
    test_ip: str = TEST_SERVER_IP,
    prod_ip: str = PROD_SERVER_IP,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    healthcheck_url: str = "http://127.0.0.1:8001/health",
    include_ragflow_images: bool = False,
) -> PublishResult:
    """
    Publish the currently-running TEST containers to PROD by:
    1) On TEST: docker save the exact images used by ragflowauth-backend/frontend
    2) scp -3: copy tar + docker-compose.yml + .env from TEST to PROD
    3) On PROD: backup existing compose/.env, docker load, replace compose/.env, restart compose

    Notes:
    - Runs from the local Windows machine (uses local ssh/scp).
    - Requires key-based SSH access to both servers.
    """
    log_lines: list[str] = []

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_lines.append(f"[{ts}] {msg}")

    version_before = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
    test_version = get_server_version_info(server_ip=test_ip, app_dir=app_dir)
    if not test_version.backend_image or not test_version.frontend_image:
        return PublishResult(
            ok=False,
            log="\n".join(log_lines + [f"[ERROR] unable to detect test images: {test_version}"]),
            version_before=version_before,
            version_after=None,
        )
    tag = (version or time.strftime("%Y%m%d_%H%M%S", time.localtime())).strip()
    releases_dir = f"{app_dir}/releases"
    tar_on_test = f"/tmp/ragflowauth_release_{tag}.tar"
    tar_on_prod = f"/tmp/ragflowauth_release_{tag}.tar"

    log(f"TEST={test_ip} PROD={prod_ip} VERSION={tag}")
    log(f"Detected TEST images: backend={test_version.backend_image} frontend={test_version.frontend_image}")
    ragflow_images: list[str] = []
    if include_ragflow_images:
        ragflow_images = _detect_ragflow_images_on_server(server_ip=test_ip)
        if ragflow_images:
            log(f"Detected TEST RAGFlow images: {', '.join(ragflow_images)}")
        else:
            log("[WARN] include_ragflow_images enabled but no RAGFlow images detected on TEST.")

    # Safety checks: ensure each environment points to its own RAGFlow.
    if not preflight_check_ragflow_base_url(
        server_ip=test_ip,
        expected_server_ip=test_ip,
        app_dir=app_dir,
        log=log,
        role_name="TEST",
    ):
        log("[ERROR] Preflight check failed; refusing to publish (TEST base_url mismatch).")
        return PublishResult(False, "\n".join(log_lines), version_before, None)
    if not preflight_check_ragflow_base_url(
        server_ip=prod_ip,
        expected_server_ip=prod_ip,
        app_dir=app_dir,
        log=log,
        role_name="PROD",
    ):
        log("[ERROR] Preflight check failed; refusing to publish (PROD base_url mismatch).")
        return PublishResult(False, "\n".join(log_lines), version_before, None)
    if test_version.compose_path:
        log(f"Detected TEST compose: {test_version.compose_path}")
        log(f"Detected TEST env: {test_version.env_path or '(missing)'}")
    else:
        config_files = _docker_label(test_ip, "ragflowauth-backend", "com.docker.compose.project.config_files")
        working_dir = _docker_label(test_ip, "ragflowauth-backend", "com.docker.compose.project.working_dir")
        log("[WARN] docker-compose file not found on TEST; will publish by recreating PROD containers from inspect (docker run mode).")
        log(f"compose label config_files: {config_files or '(empty)'}")
        log(f"compose label working_dir: {working_dir or '(empty)'}")

    log("[1/6] Ensure release directories")
    ok, out = _ssh_cmd(test_ip, f"mkdir -p {releases_dir} && echo OK")
    if not ok:
        log(f"[ERROR] TEST mkdir failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)
    ok, out = _ssh_cmd(prod_ip, f"mkdir -p {releases_dir} && echo OK")
    if not ok:
        log(f"[ERROR] PROD mkdir failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    log("[2/6] Export images on TEST (docker save)")
    images_to_save = [test_version.backend_image, test_version.frontend_image] + ragflow_images
    # Deduplicate while keeping order
    uniq: list[str] = []
    for img in images_to_save:
        if img and img not in uniq:
            uniq.append(img)
    images_str = " ".join(uniq)
    ok, out = _ssh_cmd(
        test_ip,
        f"rm -f {tar_on_test} && docker save {images_str} -o {tar_on_test}",
    )
    if not ok:
        log(f"[ERROR] docker save failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    log("[3/6] Transfer images TEST -> PROD (scp -3)")
    log(f"scp tar: {DEFAULT_SERVER_USER}@{test_ip}:{tar_on_test} -> {DEFAULT_SERVER_USER}@{prod_ip}:{tar_on_prod}")
    ok, out = _run_local(
        [
            "scp",
            "-3",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            f"{DEFAULT_SERVER_USER}@{test_ip}:{tar_on_test}",
            f"{DEFAULT_SERVER_USER}@{prod_ip}:{tar_on_prod}",
        ],
        timeout_s=7200,
    )
    if not ok:
        log(f"[ERROR] scp tar failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    log("[4/6] Load images on PROD (docker load)")
    ok, out = _ssh_cmd(prod_ip, f"docker load -i {tar_on_prod}")
    if not ok:
        log(f"[ERROR] docker load failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    log("[5/6] Recreate PROD containers with TEST images")
    prod_backend = _docker_inspect(prod_ip, "ragflowauth-backend")
    prod_frontend = _docker_inspect(prod_ip, "ragflowauth-frontend")
    if not prod_backend or not prod_frontend:
        log("[WARN] PROD containers not found (ragflowauth-backend/frontend); falling back to bootstrap mode.")
        ok2, msg2 = bootstrap_server_containers(
            server_ip=prod_ip,
            backend_image=test_version.backend_image,
            frontend_image=test_version.frontend_image,
            healthcheck_url=healthcheck_url,
            log=log,
            app_dir=app_dir,
        )
        if not ok2:
            log(f"[ERROR] bootstrap failed: {msg2}")
            return PublishResult(False, "\n".join(log_lines), version_before, None)

        version_after = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
        log("Publish completed (bootstrap mode)")
        return PublishResult(True, "\n".join(log_lines), version_before, version_after)

    network_mode = str((prod_backend.get("HostConfig") or {}).get("NetworkMode") or "").strip()
    ok, out = _ensure_network(prod_ip, network_mode)
    if not ok:
        log(f"[ERROR] ensure network failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    ok, out = _ssh_cmd(prod_ip, "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true; docker rm -f ragflowauth-backend ragflowauth-frontend 2>/dev/null || true")
    if not ok:
        log(f"[ERROR] stop/rm failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    run_front = _build_recreate_from_inspect("ragflowauth-frontend", prod_frontend, new_image=test_version.frontend_image)
    run_back = _build_recreate_from_inspect("ragflowauth-backend", prod_backend, new_image=test_version.backend_image)
    log(f"run frontend: {run_front}")
    ok, out = _ssh_cmd(prod_ip, run_front)
    if not ok:
        log(f"[ERROR] run frontend failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)
    if out:
        log(f"frontend started: {(out or '').strip()}")
    log(f"run backend: {run_back}")
    ok, out = _ssh_cmd(prod_ip, run_back)
    if not ok:
        log(f"[ERROR] run backend failed: {out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)
    if out:
        log(f"backend started: {(out or '').strip()}")

    log("[6/6] Health check on PROD")
    ok, out = _wait_prod_ready(prod_ip=prod_ip, healthcheck_url=healthcheck_url)
    if not ok:
        log(f"[ERROR] healthcheck failed:\n{out}")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    version_after = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
    log("Publish completed")
    return PublishResult(True, "\n".join(log_lines), version_before, version_after)


def recreate_server_containers_from_inspect(
    *,
    server_ip: str,
    backend_image: str,
    frontend_image: str,
    healthcheck_url: str,
    log,
) -> tuple[bool, str]:
    """
    Recreate ragflowauth-frontend/backend on a server by:
    - inspecting current containers for ports/mounts/env/network/restart policy
    - removing existing containers
    - running new containers with the provided images
    - waiting for healthcheck
    """
    prod_backend = _docker_inspect(server_ip, "ragflowauth-backend")
    prod_frontend = _docker_inspect(server_ip, "ragflowauth-frontend")
    if not prod_backend or not prod_frontend:
        return False, "containers not found (ragflowauth-backend/frontend)"

    network_mode = str((prod_backend.get("HostConfig") or {}).get("NetworkMode") or "").strip()
    ok, out = _ensure_network(server_ip, network_mode)
    if not ok:
        return False, f"ensure network failed: {out}"

    ok, out = _ssh_cmd(
        server_ip,
        "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true; "
        "docker rm -f ragflowauth-backend ragflowauth-frontend 2>/dev/null || true",
    )
    if not ok:
        return False, f"stop/rm failed: {out}"

    run_front = _build_recreate_from_inspect("ragflowauth-frontend", prod_frontend, new_image=frontend_image)
    run_back = _build_recreate_from_inspect("ragflowauth-backend", prod_backend, new_image=backend_image)
    log(f"run frontend: {run_front}")
    ok, out = _ssh_cmd(server_ip, run_front)
    if not ok:
        return False, f"run frontend failed: {out}"
    if out:
        log(f"frontend started: {(out or '').strip()}")

    log(f"run backend: {run_back}")
    ok, out = _ssh_cmd(server_ip, run_back)
    if not ok:
        return False, f"run backend failed: {out}"
    if out:
        log(f"backend started: {(out or '').strip()}")

    ok, out = _wait_prod_ready(prod_ip=server_ip, healthcheck_url=healthcheck_url)
    if not ok:
        return False, f"healthcheck failed:\n{out}"
    return True, "OK"


def bootstrap_server_containers(
    *,
    server_ip: str,
    backend_image: str,
    frontend_image: str,
    healthcheck_url: str,
    log,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    network_name: str = "ragflowauth-network",
    frontend_port: int = 3001,
    backend_port: int = 8001,
) -> tuple[bool, str]:
    """
    First-time deployment fallback when target server has no existing containers to inspect.

    This uses a fixed, known-good docker run layout that matches the project deployment conventions:
    - host app dir: /opt/ragflowauth (or `app_dir`)
    - bind mounts for data/uploads/configs/backups
    - optional /mnt/replica mount
    """
    log(f"[BOOTSTRAP] No existing containers detected; creating new containers on {server_ip} (docker run mode).")

    # Ensure required directories exist
    ok, out = _ssh_cmd(
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
    for p in required_files:
        ok, out = _ssh_cmd(server_ip, f"test -f {p} && echo OK || echo MISSING")
        if (out or "").strip().endswith("MISSING"):
            missing.append(p)
    for p in required_dirs:
        ok, out = _ssh_cmd(server_ip, f"test -d {p} && echo OK || echo MISSING")
        if (out or "").strip().endswith("MISSING"):
            missing.append(p)

    if missing:
        log("[BOOTSTRAP] Missing required files/dirs on target server:")
        for p in missing:
            log(f"[BOOTSTRAP]  - {p}")
        return False, "missing required deployment artifacts under app_dir"

    # Optional backup config (can be absent; backend will use defaults).
    ok, out = _ssh_cmd(server_ip, f"test -f {app_dir}/backup_config.json && echo OK || echo ''")
    has_backup_cfg = bool((out or "").strip())
    if not has_backup_cfg:
        log("[BOOTSTRAP] Note: backup_config.json not found; backup will use default target_dir inside container.")

    ok, out = _ensure_network(server_ip, network_name)
    if not ok:
        return False, f"ensure network failed: {out}"

    ok, out = _ssh_cmd(
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
    ok, out = _ssh_cmd(server_ip, run_front)
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
    ok, out = _ssh_cmd(server_ip, run_back)
    if not ok:
        return False, f"run backend failed: {out}"
    if out:
        log(f"[BOOTSTRAP] backend started: {(out or '').strip()}")

    ok, out = _wait_prod_ready(prod_ip=server_ip, healthcheck_url=healthcheck_url)
    if not ok:
        return False, f"healthcheck failed:\n{out}"
    return True, "OK"
