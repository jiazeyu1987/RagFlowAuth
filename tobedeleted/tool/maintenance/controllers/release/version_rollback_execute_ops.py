from ._shared import _delegate, _tool_mod


def rollback_prod_to_selected_version(app, *args, **kwargs):
    return _delegate(app, "_rollback_prod_to_selected_version_impl", "rollback_prod_to_selected_version", *args, **kwargs)


def rollback_prod_to_selected_version_impl(app):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file
    PROD_SERVER_IP = tool_mod.PROD_SERVER_IP
    feature_rollback_ragflowauth_to_version = tool_mod.feature_rollback_ragflowauth_to_version

    version = (getattr(self, "rollback_version_var", None).get() if hasattr(self, "rollback_version_var") else "").strip()
    if not version:
        messagebox.showwarning("提示", "请先选择要回滚的版本")
        return

    confirm = messagebox.askyesno(
        "二次确认",
        f"即将对【正式服务器 {PROD_SERVER_IP}】执行版本回滚：\n\n"
        f"- 版本：{version}\n"
        f"- 影响：ragflowauth-backend / ragflowauth-frontend 会被重建\n\n"
        "确定继续吗？",
    )
    if not confirm:
        return

    def worker():
        try:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text=f"回滚中... {version}")
            result = feature_rollback_ragflowauth_to_version(server_ip=PROD_SERVER_IP, version=version)
            if hasattr(self, "release_log_text"):
                self.root.after(0, lambda: self.release_log_text.insert(tk.END, (result.log or "") + "\n"))
            if hasattr(self, "status_bar"):
                self.root.after(
                    0,
                    lambda: self.status_bar.config(text=f"回滚完成：{'成功' if result.ok else '失败'}"),
                )
            if result.ok:
                self._record_release_event(event="PROD(ROLLBACK)", server_ip=PROD_SERVER_IP, version=version, details="")
        except Exception as e:
            log_to_file(f"[Rollback] failed: {e}", "ERROR")
            if hasattr(self, "status_bar"):
                self.root.after(0, lambda: self.status_bar.config(text="回滚失败"))

    self.task_runner.run(name="publish_local_to_test", fn=worker)
