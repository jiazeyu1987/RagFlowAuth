from ._shared import (
    _tool_mod,
    TEXT_CLEANUP_RESULT_TITLE,
    TEXT_ERROR_TITLE,
    TEXT_SHOW_CONTAINERS_REMOVED,
    TEXT_STATUS_CLEANUP_IMAGES,
    TEXT_STATUS_CLEANUP_IMAGES_DONE,
    TEXT_STATUS_CLEANUP_IMAGES_FAILED,
)


def cleanup_docker_images(app, *args, **kwargs):
    return cleanup_docker_images_impl(app, *args, **kwargs)


def cleanup_docker_images_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    app.status_bar.config(text=TEXT_STATUS_CLEANUP_IMAGES)

    def execute_refactored():
        try:
            if not app.ssh_executor:
                app.update_ssh_executor()
            result = tool_mod.feature_cleanup_docker_images(ssh=app.ssh_executor, log=tool_mod.log_to_file)
            app.status_bar.config(text=TEXT_STATUS_CLEANUP_IMAGES_DONE)
            app.show_text_window(TEXT_CLEANUP_RESULT_TITLE, result.summary())
        except Exception as e:
            app.status_bar.config(text=TEXT_STATUS_CLEANUP_IMAGES_FAILED)
            tool_mod.log_to_file(f"[CLEANUP-IMAGES] ERROR: {e}", "ERROR")
            app.show_text_window(TEXT_ERROR_TITLE, f"[RED]\u955c\u50cf\u6e05\u7406\u5931\u8d25\uff1a{str(e)}[/RED]")

    app.task_runner.run(name="docker_cleanup_images_refactored", fn=execute_refactored)


def show_containers_with_mounts(app, *args, **kwargs):
    return show_containers_with_mounts_impl(app, *args, **kwargs)


def show_containers_with_mounts_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    try:
        if hasattr(app, "status_bar"):
            app.status_bar.config(text=TEXT_SHOW_CONTAINERS_REMOVED)
    except Exception:
        pass

    tool_mod.log_to_file("[CONTAINER-CHECK] (removed) show_containers_with_mounts was called; no-op.", "WARN")
    return
