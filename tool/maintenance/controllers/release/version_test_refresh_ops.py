from ._shared import _delegate, _tool_mod


def refresh_release_test_versions(app, *args, **kwargs):
    return _delegate(app, "_refresh_release_test_versions_impl", "refresh_release_test_versions", *args, **kwargs)


def refresh_release_test_versions_impl(app):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    log_to_file = tool_mod.log_to_file
    TEST_SERVER_IP = tool_mod.TEST_SERVER_IP
    feature_get_server_version_info = tool_mod.feature_get_server_version_info

    def worker():
        try:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="刷新测试版本...")
            test_info = feature_get_server_version_info(server_ip=TEST_SERVER_IP)
            if hasattr(self, "release_test_before_text"):
                self.release_test_before_text.delete("1.0", tk.END)
                self.release_test_before_text.insert(tk.END, self._format_version_info(test_info))
            if hasattr(self, "release_test_after_text"):
                self.release_test_after_text.delete("1.0", tk.END)
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="刷新测试版本：成功")
        except Exception as e:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="刷新测试版本：失败")
            log_to_file(f"[Release] Refresh test version failed: {e}", "ERROR")

    self.task_runner.run(name="publish_test_to_prod", fn=worker)
