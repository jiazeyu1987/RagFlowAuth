from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_backup_tab(app) -> None:
    """Build the '备份管理' tab UI. Callbacks remain on the RagflowAuthTool instance."""
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  备份管理  ")

    title_label = ttk.Label(tab, text="服务器备份管理", font=("Arial", 14, "bold"))
    title_label.pack(pady=20)

    backup_frame = ttk.LabelFrame(tab, text="备份操作", padding=10)
    backup_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    tools = [
        {
            "title": "查看最近的备份",
            "desc": "列出服务器上最近的备份目录",
            "cmd": "ls -lht /opt/ragflowauth/data/backups/ | head -10",
        },
        {
            "title": "查看备份磁盘使用",
            "desc": "显示备份占用的磁盘空间",
            "cmd": "du -sh /opt/ragflowauth/data/backups/* | sort -hr",
        },
        {
            "title": "查看 Windows 共享备份",
            "desc": "查看同步到 Windows 共享的备份",
            "cmd": "ls -lht /mnt/replica/RagflowAuth/ | head -10",
        },
        {
            "title": "检查 SMB 挂载状态",
            "desc": "验证 Windows 共享是否正确挂载",
            "cmd": "df -h | grep replica",
        },
        {
            "title": "取消当前备份任务（强制释放 409/卡住）",
            "desc": "取消当前服务器正在运行/排队的备份任务（best-effort，会在 heartbeat 处中断长命令）",
            "cmd": "__cancel_active_backup_job__",
        },
    ]

    for tool in tools:
        frame = ttk.LabelFrame(backup_frame, text=tool["title"], padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        desc = ttk.Label(frame, text=tool["desc"], foreground="gray", wraplength=600)
        desc.pack(anchor=tk.W, pady=(0, 5))

        btn = ttk.Button(
            frame,
            text="执行",
            command=lambda cmd=tool["cmd"]: app.execute_ssh_command(cmd),
            width=15,
        )
        btn.pack(anchor=tk.W)
