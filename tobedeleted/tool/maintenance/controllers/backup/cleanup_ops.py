from ._shared import (
    _tool_mod,
    TEXT_CLEANUP_CONFIRM_TITLE,
    TEXT_CLEANUP_DONE_TITLE,
    TEXT_CLEANUP_RUNNING,
)


def cleanup_old_backups(app, *args, **kwargs):
    return cleanup_old_backups_impl(app, *args, **kwargs)


def cleanup_old_backups_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    try:
        days = int((app.backup_keep_days_var.get() or "30").strip())
    except Exception:
        days = 30

    if days < 1:
        days = 1
    if days > 3650:
        days = 3650

    confirm_msg = (
        f"\u786e\u5b9a\u8981\u5220\u9664\u8d85\u8fc7 {days} \u5929\u7684\u6240\u6709\u5907\u4efd\u5417\uff1f\n\n"
        f"\u8fd9\u5c06\u5220\u9664\u4ee5\u4e0b\u4e24\u4e2a\u76ee\u5f55\u4e2d\u8d85\u8fc7 {days} \u5929\u7684\u76ee\u5f55\uff1a\n"
        "- /opt/ragflowauth/data/backups/\n"
        "- /opt/ragflowauth/backups/"
    )
    confirm = tool_mod.messagebox.askyesno(TEXT_CLEANUP_CONFIRM_TITLE, confirm_msg)
    if not confirm:
        return

    app.backup_files_status.config(text=TEXT_CLEANUP_RUNNING)
    app.root.update()

    def cleanup():
        cmd1 = f"find /opt/ragflowauth/data/backups/ -maxdepth 1 -type d -mtime +{days} -exec rm -rf {{}} + 2>/dev/null"
        cmd2 = f"find /opt/ragflowauth/backups/ -maxdepth 1 -type d -mtime +{days} -exec rm -rf {{}} + 2>/dev/null"

        app.ssh_executor.execute(cmd1)
        app.ssh_executor.execute(cmd2)

        app.root.after(0, app.refresh_backup_files)
        app.root.after(
            0,
            lambda: tool_mod.messagebox.showinfo(TEXT_CLEANUP_DONE_TITLE, f"\u8d85\u8fc7 {days} \u5929\u7684\u65e7\u5907\u4efd\u5df2\u5220\u9664"),
        )

    app.task_runner.run(name="docker_cleanup_images", fn=cleanup)

