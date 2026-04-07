def build_release_local_ui_logger(app, *, tk):
    def ui_log(line: str) -> None:
        if not hasattr(app, "release_local_log_text"):
            return

        def _append() -> None:
            try:
                app.release_local_log_text.insert(tk.END, line + "\n")
                app.release_local_log_text.see(tk.END)
            except Exception:
                pass

        try:
            app.root.after(0, _append)
        except Exception:
            pass

    return ui_log


def render_test_versions(app, *, result, tk):
    # Show before/after on test
    if result.version_before and hasattr(app, "release_test_before_text"):
        app.release_test_before_text.delete("1.0", tk.END)
        app.release_test_before_text.insert(tk.END, app._format_version_info(result.version_before))
    if result.version_after and hasattr(app, "release_test_after_text"):
        app.release_test_after_text.delete("1.0", tk.END)
        app.release_test_after_text.insert(tk.END, app._format_version_info(result.version_after))
