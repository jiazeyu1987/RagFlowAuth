from ._shared import _delegate, _tool_mod


def restart_ragflow_and_ragflowauth(app, *args, **kwargs):
    return _delegate(app, "_restart_ragflow_and_ragflowauth_impl", "restart_ragflow_and_ragflowauth", *args, **kwargs)


def restart_ragflow_and_ragflowauth_impl(app):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file
    feature_restart_ragflow_and_ragflowauth = tool_mod.feature_restart_ragflow_and_ragflowauth

    confirm = messagebox.askyesno(
        "二次确认",
        f"即将在服务器 {self.config.environment}（{self.config.user}@{self.config.ip}）重启：\n\n"
        f"- ragflow_compose-*（RAGFlow 相关容器）\n"
        f"- ragflowauth-backend / ragflowauth-frontend\n\n"
        "确定继续吗？",
    )
    if not confirm:
        return

    server_ip = self.config.ip
    server_user = self.config.user

    if hasattr(self, "status_bar"):
        self.status_bar.config(text="正在重启服务...")

    def do_work():
        return feature_restart_ragflow_and_ragflowauth(server_ip=server_ip, server_user=server_user)

    def on_done(res):
        if not res.ok or not res.value:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="重启服务：失败")
            return

        result = res.value
        log_to_file(result.log, "INFO" if result.ok else "ERROR")
        if hasattr(self, "status_bar"):
            self.status_bar.config(text="重启服务：完成" if result.ok else "重启服务：完成（有警告）")
        self.show_text_window("重启服务结果", result.log)

    self.task_runner.run(name="restart_ragflow_and_ragflowauth", fn=do_work, on_done=on_done)
