from .transfer_phase_6_start_ops import start_restore_phase_6
from .transfer_phase_7_verify_ops import verify_restore_phase_7


def run_restore_phases_6_and_7(self, *, log_to_file, messagebox):
    self.append_restore_log("\n[6/7] 启动 Docker 容器...")
    self.update_restore_status("正在启动容器...")

    ragflowauth_reason = start_restore_phase_6(self)
    verify_restore_phase_7(
        self,
        ragflowauth_reason=ragflowauth_reason,
        log_to_file=log_to_file,
        messagebox=messagebox,
    )
