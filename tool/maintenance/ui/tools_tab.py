from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_tools_tab(app) -> None:
    """Build the '工具' tab UI. Callbacks remain on the RagflowAuthTool instance."""
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  工具  ")

    canvas = tk.Canvas(tab)
    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    tools = [
        {
            "title": "清理 Docker 镜像",
            "desc": "清理服务器上未使用的 Docker 镜像，释放磁盘空间（仅保留当前运行的镜像）",
            "cmd": "__cleanup_docker_images__",
        },
        {
            "title": "挂载 Windows 共享",
            "desc": "挂载 Windows 网络共享到服务器（固定挂载到 /mnt/replica）",
            "cmd": "__mount_windows_share__",
        },
        {
            "title": "卸载 Windows 共享",
            "desc": "卸载 Windows 网络共享（停止自动备份同步）",
            "cmd": "__unmount_windows_share__",
        },
        {
            "title": "检查挂载状态",
            "desc": "检查 Windows 共享挂载状态和可用空间",
            "cmd": "__check_mount_status__",
        },
        {
            "title": "快速部署",
            "desc": "快速部署到服务器（使用 Windows 本地构建的镜像）",
            "cmd": "quick-deploy",
        },
        {
            "title": "快速重启容器",
            "desc": "使用现有镜像快速重启容器（自动检测镜像标签并修复挂载）",
            "cmd": "__smart_quick_restart__",
        },
        {
            "title": "查看运行中的容器",
            "desc": "列出所有运行中的 Docker 容器及其状态（包括挂载信息）",
            "cmd": "__show_containers_with_mounts__",
        },
        {
            "title": "查看所有容器",
            "desc": "列出所有 Docker 容器（包括已停止的）",
            "cmd": "docker ps -a",
        },
        {
            "title": "查看 Docker 镜像",
            "desc": "列出所有 Docker 镜像及其大小",
            "cmd": "docker images",
        },
        {
            "title": "查看磁盘使用情况",
            "desc": "显示 Docker 占用的磁盘空间",
            "cmd": "docker system df",
        },
        {
            "title": "查看后端日志",
            "desc": "显示后端容器最近的日志输出",
            "cmd": "docker logs --tail 50 ragflowauth-backend",
        },
        {
            "title": "查看前端日志",
            "desc": "显示前端容器最近的日志输出",
            "cmd": "docker logs --tail 50 ragflowauth-frontend",
        },
        {
            "title": "重启所有容器",
            "desc": "重启 RagflowAuth 的所有容器",
            "cmd": "docker restart ragflowauth-backend ragflowauth-frontend",
        },
        {
            "title": "停止所有容器",
            "desc": "停止 RagflowAuth 的所有容器",
            "cmd": "docker stop ragflowauth-backend ragflowauth-frontend",
        },
        {
            "title": "启动所有容器",
            "desc": "启动 RagflowAuth 的所有容器",
            "cmd": "docker start ragflowauth-backend ragflow-frontend",
        },
    ]

    grid_frame = ttk.Frame(scrollable_frame)
    grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    for i, tool in enumerate(tools):
        row = i // 3
        col = i % 3

        tool_frame = ttk.Frame(grid_frame, relief="ridge", borderwidth=1)
        tool_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        grid_frame.columnconfigure(col, weight=1)
        grid_frame.rowconfigure(row, weight=1)

        btn = ttk.Button(
            tool_frame,
            text=tool["title"],
            command=lambda cmd=tool["cmd"]: app.execute_ssh_command(cmd),
            style="Large.TButton",
        )
        btn.pack(fill=tk.X, expand=True, pady=(8, 4), padx=8)

        desc_label = ttk.Label(
            tool_frame,
            text=tool["desc"],
            wraplength=250,
            foreground="gray",
            font=("Arial", 10),
            justify="left",
            anchor="w",
        )
        desc_label.pack(fill=tk.BOTH, expand=True, pady=(0, 8), padx=8)

