from ._shared import _delegate, _tool_mod


def stop_ragflow_and_ragflowauth(app, *args, **kwargs):
    return _delegate(app, "_stop_ragflow_and_ragflowauth_impl", "stop_ragflow_and_ragflowauth", *args, **kwargs)


def stop_ragflow_and_ragflowauth_impl(app):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file
    feature_stop_ragflow_and_ragflowauth = tool_mod.feature_stop_ragflow_and_ragflowauth

    confirm = messagebox.askyesno(
        "二次确认",
        f"即将在服务器 {self.config.environment}（{self.config.user}@{self.config.ip}）停止：\n\n"
        f"- ragflow_compose-*（RAGFlow 相关容器）\n"
        f"- ragflowauth-backend / ragflowauth-frontend\n\n"
        "这会导致业务不可用，确定继续吗？",
    )
    if not confirm:
        return

    server_ip = self.config.ip
    server_user = self.config.user

    if hasattr(self, "status_bar"):
        self.status_bar.config(text="正在停止服务...")

    def do_work():
        return feature_stop_ragflow_and_ragflowauth(server_ip=server_ip, server_user=server_user)

    def on_done(res):
        if not res.ok or not res.value:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="停止服务：失败")
            return

        result = res.value
        log_to_file(result.log, "INFO" if result.ok else "ERROR")
        if hasattr(self, "status_bar"):
            self.status_bar.config(text="停止服务：完成" if result.ok else "停止服务：完成（有警告）")
        self.show_text_window("停止服务结果", result.log)

    self.task_runner.run(name="stop_ragflow_and_ragflowauth", fn=do_work, on_done=on_done)
