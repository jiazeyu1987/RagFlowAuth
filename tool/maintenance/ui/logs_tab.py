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
        {
            "title": "实时后端日志",
            "desc": "实时显示后端容器日志（关闭窗口可停止）。",
            "cmd": "docker logs -f ragflowauth-backend",
        },
        {
            "title": "实时前端日志",
            "desc": "实时显示前端容器日志（关闭窗口可停止）。",
            "cmd": "docker logs -f ragflowauth-frontend",
        },
        {
            "title": "后端最近日志（tail 300）",
            "desc": "快速查看后端容器最近 300 行日志（适合定位刚发生的错误）。",
            "cmd": "docker logs --tail 300 ragflowauth-backend 2>&1 || true",
        },
        {
            "title": "前端最近日志（tail 300）",
            "desc": "快速查看前端容器最近 300 行日志（适合定位刚发生的错误）。",
            "cmd": "docker logs --tail 300 ragflowauth-frontend 2>&1 || true",
        },
        {
            "title": "RAGFlow 状态 + 日志（compose）",
            "desc": "查看 RAGFlow compose 容器状态并输出最近 200 行日志。",
            "cmd": "cd /opt/ragflowauth/ragflow_compose && docker compose ps 2>&1 || true; echo '---'; docker compose logs --tail 200 2>&1 || true",
        },
        {
            "title": "查看系统日志",
            "desc": "显示系统最近 50 行日志（需要 systemd/journalctl）。",
            "cmd": "journalctl -n 50 --no-pager",
        },
        {
            "title": "查看 Docker 服务日志",
            "desc": "显示 Docker 服务最近 200 行日志（需要 systemd/journalctl）。",
            "cmd": "journalctl -u docker -n 200 --no-pager",
        },
        {
            "title": "容器状态快照（ragflowauth + ragflow_compose）",
            "desc": "快速查看相关容器的镜像与状态（非日志，但排障必备）。",
            "cmd": "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' 2>&1 | grep -E '^(ragflowauth-|ragflow_compose-)' || true",
        },
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
