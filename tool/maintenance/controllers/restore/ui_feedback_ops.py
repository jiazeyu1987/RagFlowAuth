from ._shared import _tool_mod


def append_restore_log(app, text):
    return append_restore_log_impl(app, text)


def append_restore_log_impl(app, text):
    tool_mod = _tool_mod()
    log_to_file = tool_mod.log_to_file
    tk = tool_mod.tk
    threading = tool_mod.threading

    log_to_file(f"[RESTORE] {text}", "INFO")

    def _update():
        app.restore_output.config(state=tk.NORMAL)
        app.restore_output.insert(tk.END, text + "\n")
        app.restore_output.see(tk.END)
        app.restore_output.config(state=tk.DISABLED)
        app.restore_output.update_idletasks()

    if threading.current_thread() is threading.main_thread():
        _update()
    else:
        app.root.after(0, _update)


def update_restore_status(app, text):
    return update_restore_status_impl(app, text)


def update_restore_status_impl(app, text):
    tool_mod = _tool_mod()
    log_to_file = tool_mod.log_to_file
    threading = tool_mod.threading

    log_to_file(f"[RESTORE-STATUS] {text}", "INFO")

    def _update():
        app.restore_status_label.config(text=text)

    if threading.current_thread() is threading.main_thread():
        _update()
    else:
        app.root.after(0, _update)


def stop_restore_progress(app):
    return stop_restore_progress_impl(app)


def stop_restore_progress_impl(app):
    tool_mod = _tool_mod()
    tk = tool_mod.tk
    threading = tool_mod.threading

    def _update():
        app.restore_progress.stop()
        app.restore_btn.config(state=tk.NORMAL)
        if hasattr(app, "restore_start_btn"):
            app.restore_start_btn.config(state=tk.NORMAL)

    if threading.current_thread() is threading.main_thread():
        _update()
    else:
        app.root.after(0, _update)
