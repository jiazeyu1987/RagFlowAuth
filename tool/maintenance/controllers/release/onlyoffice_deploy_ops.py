from pathlib import Path

from ._shared import _tool_mod


def deploy_onlyoffice_to_server(app, *, server_ip: str, display_name: str) -> None:
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    tk = tool_mod.tk
    log_to_file = tool_mod.log_to_file
    feature_deploy_onlyoffice_from_local = tool_mod.feature_deploy_onlyoffice_from_local

    if not messagebox.askyesno(
        "确认部署 ONLYOFFICE",
        f"确认要把本机 ONLYOFFICE 发布到{display_name}服务器 {server_ip} 吗？\n\n"
        "注意：这会重建目标服务器的 onlyoffice 容器和 ragflowauth-backend 容器。",
    ):
        return

    if hasattr(self, "onlyoffice_log_text"):
        try:
            self.onlyoffice_log_text.delete("1.0", tk.END)
        except Exception:
            pass
    if hasattr(self, "status_bar"):
        self.status_bar.config(text=f"ONLYOFFICE 发布中... {display_name} {server_ip}")

    log_to_file(f"[OnlyOfficeDeploy] Start local->{display_name} ({server_ip})", "INFO")

    def worker():
        def ui_log(line: str) -> None:
            if not hasattr(self, "onlyoffice_log_text"):
                return

            def _append() -> None:
                try:
                    self.onlyoffice_log_text.insert(tk.END, line + "\n")
                    self.onlyoffice_log_text.see(tk.END)
                except Exception:
                    pass

            try:
                self.root.after(0, _append)
            except Exception:
                pass

        try:
            result = feature_deploy_onlyoffice_from_local(server_ip=server_ip, ui_log=ui_log)
            level = "INFO" if result.ok else "ERROR"
            for line in (result.log or "").splitlines():
                log_to_file(f"[OnlyOfficeDeploy] {line}", level)

            if result.ok:
                ui_log("[DONE] ONLYOFFICE 发布成功")
                if hasattr(self, "status_bar"):
                    self.root.after(0, lambda: self.status_bar.config(text=f"ONLYOFFICE 发布成功：{display_name} {server_ip}"))
            else:
                ui_log("[DONE] ONLYOFFICE 发布失败（请查看上方日志）")
                if hasattr(self, "status_bar"):
                    self.root.after(0, lambda: self.status_bar.config(text=f"ONLYOFFICE 发布失败：{display_name} {server_ip}"))
        except Exception as e:
            log_to_file(f"[OnlyOfficeDeploy] exception: {e}", "ERROR")
            ui_log(f"[ERROR] {e}")
            if hasattr(self, "status_bar"):
                self.root.after(0, lambda: self.status_bar.config(text=f"ONLYOFFICE 发布失败：{display_name} {server_ip}"))

    self.task_runner.run(name=f"deploy_onlyoffice_{server_ip}", fn=worker)
