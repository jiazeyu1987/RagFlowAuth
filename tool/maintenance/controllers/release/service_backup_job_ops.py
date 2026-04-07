from ._shared import _tool_mod, _delegate

def kill_running_backup_job(app, *args, **kwargs):
    return _delegate(app, "_kill_running_backup_job_impl", "kill_running_backup_job", *args, **kwargs)

def kill_running_backup_job_impl(app):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file
    feature_kill_running_backup_job = tool_mod.feature_kill_running_backup_job

    """
    Force-stop the currently running DataSecurity backup job on the selected server.

    This will:
    - mark the active job as canceling/failed + release sqlite lock (best-effort)
    - restart ragflowauth-backend container to terminate the running backup thread
    """
    confirm = messagebox.askyesno(
        "二次确认",
        f"即将强制终止【备份任务】（并重启 ragflowauth-backend）于服务器 {self.config.environment}（{self.config.user}@{self.config.ip}）。\n\n"
        "这会中断正在进行的备份，可能导致本次备份不完整。\n\n"
        "确定继续吗？",
    )
    if not confirm:
        return

    server_ip = self.config.ip
    server_user = self.config.user

    if hasattr(self, "status_bar"):
        self.status_bar.config(text="正在终止备份任务...")

    def do_work():
        return feature_kill_running_backup_job(server_ip=server_ip, server_user=server_user)

    def on_done(res):
        if not res.ok or not res.value:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="终止备份任务：失败")
            return

        result = res.value
        log_to_file(result.log, "INFO" if result.ok else "ERROR")
        if hasattr(self, "status_bar"):
            self.status_bar.config(text="终止备份任务：完成" if result.ok else "终止备份任务：完成（有警告）")
        self.show_text_window("终止备份任务结果", result.log)

    self.task_runner.run(name="kill_running_backup_job", fn=do_work, on_done=on_done)
