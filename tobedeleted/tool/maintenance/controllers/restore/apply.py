from ._shared import _tool_mod
from .restore_apply_confirm_ops import confirm_restore_plan
from .restore_apply_precheck_ops import (
    ensure_restore_selection,
    enforce_test_base_url_before_restore,
)
from .restore_apply_ui_ops import prepare_restore_ui_before_run

def restore_data(app, *args, **kwargs):
    return restore_data_impl(app, *args, **kwargs)

def restore_data_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    SSHExecutor = tool_mod.SSHExecutor
    TEST_SERVER_IP = tool_mod.TEST_SERVER_IP
    log_to_file = tool_mod.log_to_file
    tk = tool_mod.tk

    if not ensure_restore_selection(self, log_to_file=log_to_file, messagebox=messagebox):
        return

    # 还原仅允许在测试服务器执行（固定）
    self.ssh_executor = SSHExecutor(self.restore_target_ip, self.restore_target_user)

    if not enforce_test_base_url_before_restore(
        self,
        test_server_ip=TEST_SERVER_IP,
        log_to_file=log_to_file,
        messagebox=messagebox,
    ):
        return

    restore_type = confirm_restore_plan(self, messagebox=messagebox, log_to_file=log_to_file)
    if restore_type is None:
        return

    prepare_restore_ui_before_run(self, tk=tk)
    self.task_runner.run(name="restore_data", fn=self._execute_restore)
