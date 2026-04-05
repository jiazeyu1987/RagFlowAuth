from ._shared import _tool_mod, _delegate

TEXT_REFRESH_RELEASE_HISTORY_LOADING = "Refreshing release history..."
TEXT_REFRESH_RELEASE_HISTORY_FAILED = "Refresh release history failed"
TEXT_REFRESH_RELEASE_HISTORY_DONE = "Release history refreshed"

def refresh_release_history(app, *args, **kwargs):
    return refresh_release_history_impl(app, *args, **kwargs)

def refresh_release_history_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    if hasattr(app, "status_bar"):
        app.status_bar.config(text=TEXT_REFRESH_RELEASE_HISTORY_LOADING)

    def do_work():
        return tool_mod.feature_load_release_history(tail_lines=220)

    def on_done(res):
        if not res.ok or not res.value:
            if hasattr(app, "status_bar"):
                app.status_bar.config(text=TEXT_REFRESH_RELEASE_HISTORY_FAILED)
            return

        view = res.value
        if hasattr(app, "release_history_text"):
            try:
                app.release_history_text.delete("1.0", tool_mod.tk.END)
                app.release_history_text.insert(tool_mod.tk.END, view.text)
            except Exception:
                pass
        if hasattr(app, "status_bar"):
            app.status_bar.config(text=TEXT_REFRESH_RELEASE_HISTORY_DONE)

    app.task_runner.run(name="refresh_release_history", fn=do_work, on_done=on_done)
