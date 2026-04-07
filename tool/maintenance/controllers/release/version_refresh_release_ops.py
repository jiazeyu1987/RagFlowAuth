from ._shared import _tool_mod

TEXT_REFRESH_VERSION_LOADING = "Refreshing release versions..."
TEXT_REFRESH_VERSION_FAILED = "Refresh release versions failed"
TEXT_REFRESH_VERSION_SUCCESS = "Release versions refreshed"


def refresh_release_versions(app, *args, **kwargs):
    return refresh_release_versions_impl(app, *args, **kwargs)


def refresh_release_versions_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    if hasattr(app, "status_bar"):
        app.status_bar.config(text=TEXT_REFRESH_VERSION_LOADING)

    def do_work():
        return (
            tool_mod.feature_get_server_version_info(server_ip=tool_mod.TEST_SERVER_IP),
            tool_mod.feature_get_server_version_info(server_ip=tool_mod.PROD_SERVER_IP),
        )

    def on_done(res):
        if not res.ok or not res.value:
            if hasattr(app, "status_bar"):
                app.status_bar.config(text=TEXT_REFRESH_VERSION_FAILED)
            return

        test_info, prod_info = res.value
        if hasattr(app, "release_test_text"):
            app.release_test_text.delete("1.0", tool_mod.tk.END)
            app.release_test_text.insert(tool_mod.tk.END, app._format_version_info(test_info))
        if hasattr(app, "release_prod_text"):
            app.release_prod_text.delete("1.0", tool_mod.tk.END)
            app.release_prod_text.insert(tool_mod.tk.END, app._format_version_info(prod_info))
        if hasattr(app, "status_bar"):
            app.status_bar.config(text=TEXT_REFRESH_VERSION_SUCCESS)

    app.task_runner.run(name="refresh_release_versions", fn=do_work, on_done=on_done)
