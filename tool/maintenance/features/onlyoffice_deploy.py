from __future__ import annotations

import json
import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from tool.maintenance.core.constants import DEFAULT_SERVER_USER
from tool.maintenance.core.remote_staging import RemoteStagingManager
from tool.maintenance.core.ssh_executor import SSHExecutor
from tool.maintenance.core.tempdir import cleanup_dir, make_temp_dir

DEFAULT_ONLYOFFICE_IMAGE = "onlyoffice/documentserver:latest"
DEFAULT_ONLYOFFICE_CONTAINER = "onlyoffice"
DEFAULT_ONLYOFFICE_PORT = 8082
DEFAULT_BACKEND_CONTAINER = "ragflowauth-backend"
DEFAULT_BACKEND_PORT = 8001


@dataclass(frozen=True)
class DeployOnlyOfficeResult:
    ok: bool
    log: str


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
    # Strip noisy lines from some Windows OpenSSH builds.
    out = "\n".join(
        line
        for line in out.splitlines()
        if not line.startswith("close - IO is still pending on closed socket.")
    )
    return (proc.returncode == 0), out.strip()


def _sh_single_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def _quote_part(value: str) -> str:
    v = str(value)
    if any(ch in v for ch in (" ", "\t", "$", "`", "\"", "'")):
        return _sh_single_quote(v)
    return v


def _ssh(ssh: SSHExecutor, command: str, *, timeout_s: int = 900) -> tuple[bool, str]:
    ok, out = ssh.execute(command, timeout_seconds=timeout_s)
    return ok, (out or "").strip()


def _docker_inspect(ssh: SSHExecutor, container_name: str) -> dict | None:
    ok, out = _ssh(ssh, f"docker inspect {container_name} 2>/dev/null || echo '[]'", timeout_s=90)
    if not ok:
        return None
    try:
        data = json.loads(out or "[]")
    except Exception:
        return None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def _extract_env_map(inspect: dict) -> dict[str, str]:
    cfg = inspect.get("Config") or {}
    envs = cfg.get("Env") or []
    env_map: dict[str, str] = {}
    if isinstance(envs, list):
        for raw in envs:
            if not isinstance(raw, str) or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            if key and (key not in env_map):
                env_map[key] = value
    return env_map


def _build_recreate_from_inspect_with_env(
    *,
    container_name: str,
    inspect: dict,
    new_image: str,
    env_overrides: dict[str, str],
) -> str:
    host_cfg = inspect.get("HostConfig") or {}
    cfg = inspect.get("Config") or {}

    parts: list[str] = ["docker", "run", "-d", "--name", container_name]

    network_mode = str(host_cfg.get("NetworkMode") or "").strip()
    if network_mode and network_mode not in ("default", "bridge"):
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

    env_map = _extract_env_map(inspect)
    for key, value in (env_overrides or {}).items():
        env_map[str(key)] = str(value)
    for key, value in env_map.items():
        parts += ["-e", f"{key}={value}"]

    parts.append(new_image)
    return " ".join(_quote_part(p) for p in parts)


def _wait_http_ok(
    *,
    ssh: SSHExecutor,
    url: str,
    timeout_s: int,
    interval_s: int = 3,
) -> tuple[bool, str]:
    deadline = time.time() + max(5, int(timeout_s))
    last_out = ""
    while time.time() < deadline:
        ok, out = _ssh(ssh, f"curl -fsS {_quote_part(url)} >/dev/null && echo OK", timeout_s=30)
        last_out = out or ""
        if ok and "OK" in (out or ""):
            return True, "OK"
        time.sleep(interval_s)
    return False, last_out


def deploy_onlyoffice_from_local(
    *,
    server_ip: str,
    server_user: str = DEFAULT_SERVER_USER,
    image: str = DEFAULT_ONLYOFFICE_IMAGE,
    onlyoffice_container: str = DEFAULT_ONLYOFFICE_CONTAINER,
    onlyoffice_port: int = DEFAULT_ONLYOFFICE_PORT,
    backend_container: str = DEFAULT_BACKEND_CONTAINER,
    backend_port: int = DEFAULT_BACKEND_PORT,
    ui_log=None,
) -> DeployOnlyOfficeResult:
    log_lines: list[str] = []
    tmp_dir: Path | None = None
    tar_local: Path | None = None
    tar_remote: str = ""
    ssh = SSHExecutor(server_ip, server_user)

    def log(msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] {msg}"
        log_lines.append(line)
        if ui_log:
            try:
                ui_log(line)
            except Exception:
                pass

    def finish(ok: bool) -> DeployOnlyOfficeResult:
        return DeployOnlyOfficeResult(ok=ok, log="\n".join(log_lines))

    try:
        log(f"TARGET={server_user}@{server_ip}")
        log(f"ONLYOFFICE_IMAGE={image}")

        log("[1/8] Check local onlyoffice image")
        ok, out = _run_local(["docker", "image", "inspect", image], timeout_s=60)
        if not ok:
            log("[INFO] local image missing, pulling from registry")
            ok, out = _run_local(["docker", "pull", image], timeout_s=7200)
            if not ok:
                log(f"[ERROR] docker pull failed:\n{out}")
                return finish(False)

        log("[2/8] Export local onlyoffice image (docker save)")
        tmp_dir = make_temp_dir(prefix="onlyoffice_release")
        tag = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        tar_local = tmp_dir / f"onlyoffice_release_{tag}.tar"
        ok, out = _run_local(["docker", "save", image, "-o", str(tar_local)], timeout_s=7200)
        if not ok or (not tar_local.exists()):
            log(f"[ERROR] docker save failed:\n{out}")
            return finish(False)
        tar_size = int(tar_local.stat().st_size)
        log(f"[STAGING] local tar size: {tar_size} bytes")

        log("[3/8] Pick remote staging path")
        staging_mgr = RemoteStagingManager(exec_fn=lambda c: _ssh(ssh, c, timeout_s=120), log=log)
        staging_mgr.cleanup_legacy_tmp_release_files()
        pick = staging_mgr.pick_dir_for_bytes(size_bytes=tar_size)
        tar_remote = staging_mgr.join(pick.dir, tar_local.name)
        log(f"[STAGING] remote tar path: {tar_remote}")

        log("[4/8] Transfer image to target server (scp)")
        ok, out = _run_local(["scp", str(tar_local), f"{server_user}@{server_ip}:{tar_remote}"], timeout_s=7200)
        if not ok:
            log(f"[ERROR] scp failed:\n{out}")
            return finish(False)

        log("[5/8] Load image on target server (docker load)")
        ok, out = _ssh(ssh, f"docker load -i {_quote_part(tar_remote)}", timeout_s=7200)
        if not ok:
            log(f"[ERROR] docker load failed:\n{out}")
            return finish(False)
        staging_mgr.cleanup_path(tar_remote)
        tar_remote = ""

        log("[6/8] Deploy onlyoffice container")
        # Keep onlyoffice in a stable dedicated network and expose host port for browser access.
        _ssh(
            ssh,
            "docker network inspect ragflowauth-network >/dev/null 2>&1 || docker network create ragflowauth-network",
            timeout_s=60,
        )

        backend_inspect = _docker_inspect(ssh, backend_container)
        if not backend_inspect:
            log(f"[ERROR] backend container not found: {backend_container}")
            return finish(False)
        backend_image = str(((backend_inspect.get("Config") or {}).get("Image") or "")).strip()
        if not backend_image:
            log(f"[ERROR] unable to detect backend image from container: {backend_container}")
            return finish(False)

        env_map = _extract_env_map(backend_inspect)
        onlyoffice_jwt_secret = (env_map.get("ONLYOFFICE_JWT_SECRET") or "").strip() or secrets.token_hex(24)
        file_token_secret = (
            (env_map.get("ONLYOFFICE_FILE_TOKEN_SECRET") or "").strip()
            or (env_map.get("JWT_SECRET_KEY") or "").strip()
            or secrets.token_hex(24)
        )
        onlyoffice_server_url = f"http://{server_ip}:{int(onlyoffice_port)}"
        onlyoffice_api_base = f"http://{server_ip}:{int(backend_port)}"

        rm_onlyoffice = f"docker rm -f {_quote_part(onlyoffice_container)} 2>/dev/null || true"
        onlyoffice_run_parts = [
            "docker",
            "run",
            "-d",
            "--name",
            onlyoffice_container,
            "--network",
            "ragflowauth-network",
            "-p",
            f"{int(onlyoffice_port)}:80",
            "-e",
            "JWT_ENABLED=true",
            "-e",
            f"JWT_SECRET={onlyoffice_jwt_secret}",
            "-v",
            "onlyoffice_data:/var/www/onlyoffice/Data",
            "-v",
            "onlyoffice_logs:/var/log/onlyoffice",
            "-v",
            "onlyoffice_lib:/var/lib/onlyoffice",
            "--restart",
            "unless-stopped",
            image,
        ]
        run_onlyoffice = " ".join(_quote_part(p) for p in onlyoffice_run_parts)
        ok, out = _ssh(ssh, f"{rm_onlyoffice}; {run_onlyoffice}", timeout_s=1200)
        if not ok:
            log(f"[ERROR] start onlyoffice failed:\n{out}")
            return finish(False)

        log("[7/8] Recreate backend container with ONLYOFFICE env")
        backend_network = str(((backend_inspect.get("HostConfig") or {}).get("NetworkMode") or "")).strip()
        if backend_network and backend_network not in ("default", "bridge", "host", "none"):
            ok, out = _ssh(
                ssh,
                f"docker network inspect {_quote_part(backend_network)} >/dev/null 2>&1 || "
                f"docker network create {_quote_part(backend_network)}",
                timeout_s=60,
            )
            if not ok:
                log(f"[ERROR] ensure backend network failed:\n{out}")
                return finish(False)

        backend_env_overrides = {
            "ONLYOFFICE_ENABLED": "true",
            "ONLYOFFICE_SERVER_URL": onlyoffice_server_url,
            "ONLYOFFICE_PUBLIC_API_BASE_URL": onlyoffice_api_base,
            "ONLYOFFICE_JWT_SECRET": onlyoffice_jwt_secret,
            "ONLYOFFICE_FILE_TOKEN_SECRET": file_token_secret,
        }
        run_backend = _build_recreate_from_inspect_with_env(
            container_name=backend_container,
            inspect=backend_inspect,
            new_image=backend_image,
            env_overrides=backend_env_overrides,
        )
        ok, out = _ssh(
            ssh,
            f"docker stop {_quote_part(backend_container)} 2>/dev/null || true; "
            f"docker rm -f {_quote_part(backend_container)} 2>/dev/null || true; "
            f"{run_backend}",
            timeout_s=900,
        )
        if not ok:
            log(f"[ERROR] recreate backend failed:\n{out}")
            return finish(False)

        log("[8/8] Health checks")
        ok, out = _wait_http_ok(ssh=ssh, url=f"http://127.0.0.1:{int(backend_port)}/health", timeout_s=120)
        if not ok:
            log(f"[ERROR] backend health check failed: {out}")
            _, diag = _ssh(ssh, f"docker logs --tail 150 {_quote_part(backend_container)} 2>&1 || true", timeout_s=60)
            if diag:
                log(f"[DIAG] backend logs:\n{diag}")
            return finish(False)

        ok, out = _wait_http_ok(ssh=ssh, url=f"http://127.0.0.1:{int(onlyoffice_port)}/healthcheck", timeout_s=300)
        if not ok:
            log(f"[ERROR] onlyoffice health check failed: {out}")
            _, diag = _ssh(ssh, f"docker logs --tail 150 {_quote_part(onlyoffice_container)} 2>&1 || true", timeout_s=60)
            if diag:
                log(f"[DIAG] onlyoffice logs:\n{diag}")
            return finish(False)

        log("Deploy ONLYOFFICE completed")
        return finish(True)
    except Exception as e:
        log(f"[ERROR] unexpected exception: {e}")
        return finish(False)
    finally:
        if tar_remote:
            try:
                _ssh(ssh, f"rm -f {_quote_part(tar_remote)} 2>/dev/null || true", timeout_s=30)
            except Exception:
                pass
        if tar_local is not None:
            try:
                tar_local.unlink(missing_ok=True)
            except Exception:
                pass
        if tmp_dir is not None:
            cleanup_dir(tmp_dir)
