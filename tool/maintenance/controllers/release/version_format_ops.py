from ._shared import _tool_mod


def release_generate_version(app):
    tool_mod = _tool_mod()
    time = tool_mod.time
    app.release_version_var.set(time.strftime("%Y%m%d_%H%M%S", time.localtime()))


def release_version_arg(app) -> str | None:
    value = (app.release_version_var.get() or "").strip()
    return value or None


def format_version_info(info) -> str:
    if not info:
        return ""
    return (
        f"server: {info.server_ip}\n"
        f"backend_image: {info.backend_image}\n"
        f"frontend_image: {info.frontend_image}\n"
        f"compose_path: {info.compose_path}\n"
        f"env_path: {info.env_path}\n"
        f"docker-compose.yml sha256: {info.compose_sha256}\n"
        f".env sha256: {info.env_sha256}\n"
    )
