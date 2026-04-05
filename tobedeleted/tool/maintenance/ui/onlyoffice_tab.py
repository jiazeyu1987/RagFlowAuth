from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk

from tool.maintenance.core.constants import PROD_SERVER_IP, TEST_SERVER_IP


def build_onlyoffice_tab(app) -> None:
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  ONLYOFFICE  ")

    title = ttk.Label(tab, text="ONLYOFFICE 发布", font=("Arial", 14, "bold"))
    title.pack(pady=12)

    desc = ttk.Label(
        tab,
        text=(
            "用于把本机的 onlyoffice/documentserver 镜像发布到目标服务器，"
            "并在目标服务器部署 onlyoffice 容器。\n"
            "部署过程中会同步重建 ragflowauth-backend 容器并写入 ONLYOFFICE_* 环境变量。"
        ),
        foreground="gray",
        justify=tk.LEFT,
    )
    desc.pack(fill=tk.X, padx=20, pady=(0, 10))

    btn_frame = ttk.Frame(tab)
    btn_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
    ttk.Button(
        btn_frame,
        text=f"发布本机到测试机（{TEST_SERVER_IP}）",
        command=app.deploy_onlyoffice_to_test,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(
        btn_frame,
        text=f"发布本机到正式机（{PROD_SERVER_IP}）",
        command=app.deploy_onlyoffice_to_prod,
    ).pack(side=tk.LEFT, padx=5)

    log_frame = ttk.LabelFrame(tab, text="ONLYOFFICE 发布日志", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

    app.onlyoffice_log_text = scrolledtext.ScrolledText(log_frame, height=22)
    app.onlyoffice_log_text.pack(fill=tk.BOTH, expand=True)
