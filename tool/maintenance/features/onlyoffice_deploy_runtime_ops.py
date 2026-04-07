from __future__ import annotations

import json
import time
from typing import Callable


def sh_single_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def quote_part(value: str, *, sh_single_quote_fn: Callable[[str], str] = sh_single_quote) -> str:
    v = str(value)
    if any(ch in v for ch in (" ", "\t", "$", "`", "\"", "'")):
        return sh_single_quote_fn(v)
    return v


def docker_inspect(*, ssh_exec, container_name: str) -> dict | None:
    ok, out = ssh_exec(f"docker inspect {container_name} 2>/dev/null || echo '[]'", 90)
    if not ok:
        return None
    try:
        data = json.loads(out or "[]")
    except Exception:
        return None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def extract_env_map(inspect: dict) -> dict[str, str]:
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


def build_recreate_from_inspect_with_env(
    *,
    container_name: str,
    inspect: dict,
    new_image: str,
    env_overrides: dict[str, str],
    extract_env_map_fn: Callable[[dict], dict[str, str]] = extract_env_map,
    quote_part_fn: Callable[[str], str] = quote_part,
) -> str:
    host_cfg = inspect.get("HostConfig") or {}

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

    env_map = extract_env_map_fn(inspect)
    for key, value in (env_overrides or {}).items():
        env_map[str(key)] = str(value)
    for key, value in env_map.items():
        parts += ["-e", f"{key}={value}"]

    parts.append(new_image)
    return " ".join(quote_part_fn(p) for p in parts)


def wait_http_ok(
    *,
    ssh_exec,
    url: str,
    timeout_s: int,
    interval_s: int = 3,
    quote_part_fn: Callable[[str], str] = quote_part,
) -> tuple[bool, str]:
    deadline = time.time() + max(5, int(timeout_s))
    last_out = ""
    while time.time() < deadline:
        ok, out = ssh_exec(f"curl -fsS {quote_part_fn(url)} >/dev/null && echo OK", 30)
        last_out = out or ""
        if ok and "OK" in (out or ""):
            return True, "OK"
        time.sleep(interval_s)
    return False, last_out

