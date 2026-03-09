from __future__ import annotations

from typing import Any, Callable


def docker_label(*, ssh_cmd: Callable[[str, str], tuple[bool, str]], ip: str, container_name: str, label: str) -> str:
    # Use a single-quoted Go template, and a double-quoted label key inside it.
    # Avoid nesting single quotes (which breaks in /bin/sh).
    template = f'{{{{ index .Config.Labels "{label}" }}}}'
    ok, out = ssh_cmd(ip, f"docker inspect -f '{template}' {container_name} 2>/dev/null || echo ''")
    if not ok:
        return ""
    text = (out or "").strip()
    if not text:
        return ""
    return text.splitlines()[-1].strip()


def detect_compose_and_env_paths(
    *,
    ssh_cmd: Callable[[str, str], tuple[bool, str]],
    docker_label_fn: Callable[[str, str, str], str],
    ip: str,
    app_dir: str,
) -> tuple[str, str]:
    """
    Try to detect compose/.env paths from the running containers (Docker Compose labels),
    then fall back to common locations under `app_dir`.
    """
    container = "ragflowauth-backend"
    config_files = docker_label_fn(ip, container, "com.docker.compose.project.config_files")
    working_dir = docker_label_fn(ip, container, "com.docker.compose.project.working_dir")

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
        ok, out = ssh_cmd(ip, f"test -f {p} && echo FOUND || echo ''")
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
        ok, out = ssh_cmd(ip, find_cmd)
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
        ok, out = ssh_cmd(ip, f"test -f {p} && echo FOUND || echo ''")
        if ok and (out or "").strip().endswith("FOUND"):
            env_path = p
            break

    return compose_path, env_path


def sha256_of_remote_file(*, ssh_cmd: Callable[[str, str], tuple[bool, str]], ip: str, path: str) -> str:
    ok, out = ssh_cmd(ip, f"test -f {path} && sha256sum {path} | awk '{{print $1}}' || echo ''")
    if not ok:
        return ""
    text = (out or "").strip()
    if not text:
        return ""
    return text.splitlines()[-1].strip()


def docker_container_image(*, ssh_cmd: Callable[[str, str], tuple[bool, str]], ip: str, container_name: str) -> str:
    ok, out = ssh_cmd(ip, f"docker inspect -f '{{{{.Config.Image}}}}' {container_name} 2>/dev/null || echo ''")
    if not ok:
        return ""
    text = (out or "").strip()
    if not text:
        return ""
    return text.splitlines()[-1].strip()


def get_server_version_info_impl(
    *,
    server_ip: str,
    app_dir: str,
    docker_container_image_fn: Callable[[str, str], str],
    detect_compose_and_env_paths_fn: Callable[[str, str], tuple[str, str]],
    sha256_of_remote_file_fn: Callable[[str, str], str],
    version_info_factory: Callable[..., Any],
) -> Any:
    backend_image = docker_container_image_fn(server_ip, "ragflowauth-backend")
    frontend_image = docker_container_image_fn(server_ip, "ragflowauth-frontend")
    compose_path, env_path = detect_compose_and_env_paths_fn(server_ip, app_dir)
    compose_sha256 = sha256_of_remote_file_fn(server_ip, compose_path) if compose_path else ""
    env_sha256 = sha256_of_remote_file_fn(server_ip, env_path) if env_path else ""
    return version_info_factory(
        server_ip=server_ip,
        backend_image=backend_image,
        frontend_image=frontend_image,
        compose_path=compose_path,
        env_path=env_path,
        compose_sha256=compose_sha256,
        env_sha256=env_sha256,
    )
