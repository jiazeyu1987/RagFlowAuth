from ._shared import _tool_mod
from .transfer_phases import run_restore_phases_1_to_5, run_restore_phases_6_and_7


def execute_restore_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()
    self = app
    log_to_file = tool_mod.log_to_file
    messagebox = tool_mod.messagebox
    tempfile = tool_mod.tempfile
    tarfile = tool_mod.tarfile
    subprocess = tool_mod.subprocess
    time = tool_mod.time
    os = tool_mod.os

    # 执行还原流程（按阶段串行执行）
    try:
        run_restore_phases_1_to_5(
            self,
            log_to_file=log_to_file,
            messagebox=messagebox,
            tempfile=tempfile,
            tarfile=tarfile,
            subprocess=subprocess,
            time=time,
            os=os,
        )
        run_restore_phases_6_and_7(self, log_to_file=log_to_file, messagebox=messagebox)
    except Exception as e:
        error_msg = f"还原失败: {str(e)}"
        self.append_restore_log(f"\n[ERROR] {error_msg}")
        self.update_restore_status("还原失败")
        msg = f"[ERROR] {error_msg}"
        print(msg)
        log_to_file(msg, "ERROR")
        messagebox.showerror("还原失败", error_msg)

    finally:
        # 恢复按钮状态并停止进度条
        self.stop_restore_progress()
