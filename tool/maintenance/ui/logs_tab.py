from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_logs_tab(app) -> None:
    """Build the '日志查看' tab UI. Actual log fetching happens in tool.py callbacks."""
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  日志查看  ")

    title_label = ttk.Label(tab, text="实时日志查看", font=("Arial", 14, "bold"))
    title_label.pack(pady=20)

    log_frame = ttk.LabelFrame(tab, text="日志查看", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    tools = [
        {"title": "实时后端日志", "desc": "实时显示后端容器日志（Ctrl+C 停止）", "cmd": "docker logs -f ragflowauth-backend"},
        {"title": "实时前端日志", "desc": "实时显示前端容器日志（Ctrl+C 停止）", "cmd": "docker logs -f ragflowauth-frontend"},
        {"title": "查看系统日志", "desc": "显示系统最近的系统日志", "cmd": "journalctl -n 50 --no-pager"},
        {"title": "查看 Docker 服务日志", "desc": "显示 Docker 服务的日志", "cmd": "journalctl -u docker -n 50 --no-pager"},
    ]

    for tool in tools:
        frame = ttk.LabelFrame(log_frame, text=tool["title"], padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        desc = ttk.Label(frame, text=tool["desc"], foreground="gray", wraplength=600)
        desc.pack(anchor=tk.W, pady=(0, 5))

        btn = ttk.Button(
            frame,
            text="在新窗口中查看",
            command=lambda cmd=tool["cmd"]: app.open_log_window(cmd),
            width=20,
        )
        btn.pack(anchor=tk.W)

