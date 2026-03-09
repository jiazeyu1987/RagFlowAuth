from ._shared import _tool_mod, _delegate

def run_smoke_test(app, *args, **kwargs):
    return _delegate(app, "_run_smoke_test_impl", "run_smoke_test", *args, **kwargs)

def run_smoke_test_impl(app, server_ip: str):
    tool_mod = _tool_mod()
    self = app
    feature_run_smoke_test = tool_mod.feature_run_smoke_test

    """
    Run smoke tests in a background thread and render the report.
    This is a read-only operation.
    """

    if hasattr(self, "status_bar"):
        self.status_bar.config(text=f"冒烟测试运行中... {server_ip}")

    def do_work():
        return feature_run_smoke_test(server_ip=server_ip)

    def on_done(res):
        if not res.ok or not res.value:
            if hasattr(self, "status_bar"):
                self.status_bar.config(text="冒烟测试失败")
            return
        report = (res.value.report or "") + "\n"
        if hasattr(self, "smoke_output"):
            self._set_smoke_output(report)
        if hasattr(self, "status_bar"):
            self.status_bar.config(text=f"冒烟测试完成：{'通过' if res.value.ok else '失败'}")

    self.task_runner.run(name="smoke_test", fn=do_work, on_done=on_done)
