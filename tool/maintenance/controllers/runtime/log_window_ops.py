from ._shared import _tool_mod
from .log_window_stream_ops import build_tail_log_worker, build_window_queue_poller
from .log_window_ui_ops import build_log_window_ui


def open_log_window_impl(app, command):
    tool_mod = _tool_mod()
    self = app
    if not self.ssh_executor:
        self.update_ssh_executor()

    ui = build_log_window_ui(
        self,
        command=command,
        tk=tool_mod.tk,
        ttk=tool_mod.ttk,
        scrolledtext=tool_mod.scrolledtext,
    )

    tail_log_worker = build_tail_log_worker(
        self,
        command=command,
        subprocess_mod=tool_mod.subprocess,
        queue_obj=ui["queue"],
        stop_state=ui["stop_state"],
        process_holder=ui["process_holder"],
    )
    poll_queue = build_window_queue_poller(
        queue_obj=ui["queue"],
        append_fn=ui["append"],
        stop_state=ui["stop_state"],
        log_window=ui["window"],
    )

    ui["append"](f"[TARGET] {self.ssh_executor.user}@{self.ssh_executor.ip}\n$ {command}\n\n")
    self.task_runner.run(name="tail_logs", fn=tail_log_worker)
    ui["window"].after(80, poll_queue)
