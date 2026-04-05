from ._shared import _tool_mod


def refresh_ragflow_base_urls(app, *args, **kwargs):
    return refresh_ragflow_base_urls_impl(app, *args, **kwargs)


def refresh_ragflow_base_urls_impl(app, *args, **kwargs):
    """
    Refresh base_url display for Local/TEST/PROD ragflow_config.json.
    Used as a guardrail to avoid environment cross-reading.
    """
    tool_mod = _tool_mod()

    try:
        if hasattr(app, "ragflow_base_url_local_var"):
            ok, val = tool_mod.read_local_base_url(tool_mod.LOCAL_RAGFLOW_CONFIG_PATH)
            app.ragflow_base_url_local_var.set(val if ok else f"(error) {val}")
    except Exception as e:
        if hasattr(app, "ragflow_base_url_local_var"):
            app.ragflow_base_url_local_var.set(f"(error) {e}")

    if hasattr(app, "ragflow_base_url_test_var"):
        app.ragflow_base_url_test_var.set("(loading...)")
    if hasattr(app, "ragflow_base_url_prod_var"):
        app.ragflow_base_url_prod_var.set("(loading...)")

    tool_mod.log_to_file("[BASE_URL] refresh start", "DEBUG")

    def do_work():
        return (
            tool_mod.read_remote_base_url(server_ip=tool_mod.TEST_SERVER_IP, app_dir="/opt/ragflowauth", timeout_seconds=20),
            tool_mod.read_remote_base_url(server_ip=tool_mod.PROD_SERVER_IP, app_dir="/opt/ragflowauth", timeout_seconds=20),
        )

    def on_done(res):
        if not res.ok:
            err = str(res.error) if res.error else "unknown error"
            tool_mod.log_to_file(f"[BASE_URL] refresh failed: {err}", "ERROR")
            if hasattr(app, "ragflow_base_url_test_var"):
                app.ragflow_base_url_test_var.set(f"(error) {err}")
            if hasattr(app, "ragflow_base_url_prod_var"):
                app.ragflow_base_url_prod_var.set(f"(error) {err}")
            return

        if not res.value:
            tool_mod.log_to_file("[BASE_URL] refresh failed: empty result", "ERROR")
            if hasattr(app, "ragflow_base_url_test_var"):
                app.ragflow_base_url_test_var.set("(error) empty result")
            if hasattr(app, "ragflow_base_url_prod_var"):
                app.ragflow_base_url_prod_var.set("(error) empty result")
            return

        (ok_t, val_t), (ok_p, val_p) = res.value
        tool_mod.log_to_file(
            f"[BASE_URL] refresh done: test_ok={ok_t} prod_ok={ok_p} test={val_t!s} prod={val_p!s}",
            "DEBUG",
        )
        if hasattr(app, "ragflow_base_url_test_var"):
            app.ragflow_base_url_test_var.set(val_t if ok_t else f"(error) {val_t}")
        if hasattr(app, "ragflow_base_url_prod_var"):
            app.ragflow_base_url_prod_var.set(val_p if ok_p else f"(error) {val_p}")

    app.task_runner.run(name="refresh_ragflow_base_urls", fn=do_work, on_done=on_done)
