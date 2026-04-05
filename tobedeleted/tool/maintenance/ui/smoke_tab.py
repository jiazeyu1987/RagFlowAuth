from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext

from tool.maintenance.core.constants import PROD_SERVER_IP, TEST_SERVER_IP


def build_smoke_tab(app) -> None:
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  冒烟测试  ")

    title = ttk.Label(tab, text="一键冒烟测试（只读检查）", font=("Arial", 14, "bold"))
    title.pack(pady=14)

    desc = ttk.Label(
        tab,
        text=(
            "用于在测试/生产服务器快速验证：docker 可用、容器状态、后端健康检查、前端可访问、RAGFlow 可访问、/mnt/replica 挂载等。\n"
            "说明：冒烟测试为【只读】操作，不会修改服务器数据。\n"
        ),
        foreground="gray",
        justify=tk.LEFT,
    )
    desc.pack(fill=tk.X, padx=20, pady=(0, 10))

    btn_frame = ttk.Frame(tab)
    btn_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

    ttk.Button(btn_frame, text=f"运行（测试 {TEST_SERVER_IP}）", command=lambda: app.run_smoke_test(TEST_SERVER_IP)).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(btn_frame, text=f"运行（正式 {PROD_SERVER_IP}）", command=lambda: app.run_smoke_test(PROD_SERVER_IP)).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(btn_frame, text="运行（当前选择）", command=lambda: app.run_smoke_test(app.config.ip)).pack(
        side=tk.LEFT, padx=5
    )

    out_frame = ttk.LabelFrame(tab, text="冒烟测试报告", padding=10)
    out_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

    app.smoke_output = scrolledtext.ScrolledText(out_frame, height=24, font=("Consolas", 9))
    app.smoke_output.pack(fill=tk.BOTH, expand=True)

