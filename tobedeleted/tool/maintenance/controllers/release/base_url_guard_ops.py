from ._shared import _tool_mod


def guard_ragflow_base_url(app, *, role: str, stage: str, ui_log=None) -> None:
    tool_mod = _tool_mod()
    log_to_file = tool_mod.log_to_file
    ensure_local_base_url = tool_mod.ensure_local_base_url
    ensure_remote_base_url = tool_mod.ensure_remote_base_url
    LOCAL_RAGFLOW_BASE_URL = tool_mod.LOCAL_RAGFLOW_BASE_URL
    LOCAL_RAGFLOW_CONFIG_PATH = tool_mod.LOCAL_RAGFLOW_CONFIG_PATH
    TEST_SERVER_IP = tool_mod.TEST_SERVER_IP
    TEST_RAGFLOW_BASE_URL = tool_mod.TEST_RAGFLOW_BASE_URL
    PROD_SERVER_IP = tool_mod.PROD_SERVER_IP
    PROD_RAGFLOW_BASE_URL = tool_mod.PROD_RAGFLOW_BASE_URL
    _ = app

    role_norm = (role or "").strip().lower()

    def _log(msg: str) -> None:
        text = f"[BASE_URL] [{stage}] {msg}"
        log_to_file(text, "INFO")
        if ui_log:
            try:
                ui_log(text)
            except Exception:
                pass

    if role_norm == "local":
        res = ensure_local_base_url(desired=LOCAL_RAGFLOW_BASE_URL, path=LOCAL_RAGFLOW_CONFIG_PATH)
        if not res.ok:
            raise RuntimeError(f"Local base_url guard failed: {res.error}")
        _log(f"LOCAL before={res.before} after={res.after}" + (" (changed)" if res.changed else ""))
        return

    if role_norm == "test":
        ip = TEST_SERVER_IP
        desired = TEST_RAGFLOW_BASE_URL
        role_name = "TEST"
    elif role_norm == "prod":
        ip = PROD_SERVER_IP
        desired = PROD_RAGFLOW_BASE_URL
        role_name = "PROD"
    else:
        raise ValueError(f"unknown role: {role!r}")

    res = ensure_remote_base_url(
        server_ip=ip,
        desired=desired,
        app_dir="/opt/ragflowauth",
        role_name=role_name,
        log=lambda m: _log(m),
    )
    if not res.ok:
        raise RuntimeError(f"{role_name} base_url guard failed: {res.error}")
