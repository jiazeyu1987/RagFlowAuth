from ._shared import _delegate, _tool_mod


def refresh_prod_rollback_versions(app, *args, **kwargs):
    return _delegate(app, "_refresh_prod_rollback_versions_impl", "refresh_prod_rollback_versions", *args, **kwargs)


def refresh_prod_rollback_versions_impl(app):
    tool_mod = _tool_mod()
    self = app

    if hasattr(self, "status_bar"):
        self.status_bar.config(text="鍒锋柊鍙洖婊氱増鏈?..")

    def do_work():
        return tool_mod.feature_list_ragflowauth_versions(server_ip=tool_mod.PROD_SERVER_IP, limit=30)

    def on_done(res):
        if not res.ok or res.value is None:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="鍒锋柊鍙洖婊氱増鏈細澶辫触")
            return

        versions = res.value
        if hasattr(self, "rollback_version_combo"):
            self.rollback_version_combo.configure(values=versions)
            if versions and not (self.rollback_version_var.get() or "").strip():
                self.rollback_version_var.set(versions[0])
        if hasattr(self, "status_bar"):
            self.status_bar.config(text="鍒锋柊鍙洖婊氱増鏈細瀹屾垚")

    self.task_runner.run(name="refresh_prod_rollback_versions", fn=do_work, on_done=on_done)
