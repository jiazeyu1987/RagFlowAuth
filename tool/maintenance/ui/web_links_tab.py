from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_web_links_tab(app) -> None:
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  Web 管理界面  ")

    title_label = ttk.Label(tab, text="Web 管理界面快速访问", font=("Arial", 14, "bold"))
    title_label.pack(pady=20)

    button_frame = ttk.Frame(tab)
    button_frame.pack(pady=20)

    frontend_btn = ttk.Button(button_frame, text="🏠 打开 RagflowAuth 前端", command=app.open_frontend, width=30)
    frontend_btn.grid(row=0, column=0, pady=10, padx=10)

    frontend_desc = ttk.Label(
        tab,
        text="RagflowAuth 前端应用\n用户登录、知识库管理、文档管理等",
        justify=tk.CENTER,
        foreground="gray",
    )
    frontend_desc.pack(pady=(0, 10))

    portainer_btn = ttk.Button(button_frame, text="🚀 打开 Portainer", command=app.open_portainer, width=30)
    portainer_btn.grid(row=1, column=0, pady=10, padx=10)

    portainer_desc = ttk.Label(
        tab,
        text="Portainer - Docker 容器管理平台 (HTTPS 端口 9002)\n可以可视化管理容器、镜像、网络等 Docker 资源",
        justify=tk.CENTER,
        foreground="gray",
    )
    portainer_desc.pack(pady=(0, 10))

    web_btn = ttk.Button(button_frame, text="🌐 打开 Web 管理界面", command=app.open_web_console, width=30)
    web_btn.grid(row=2, column=0, pady=10, padx=10)

    app.web_desc_label = ttk.Label(
        tab,
        text="Web 管理界面 - RagflowAuth 后台管理\n" f"访问 https://{app.config.ip}:9090/ 进行后台管理",
        justify=tk.CENTER,
        foreground="gray",
    )
    app.web_desc_label.pack(pady=(0, 20))

    url_frame = ttk.LabelFrame(tab, text="自定义 URL", padding=10)
    url_frame.pack(fill=tk.X, padx=50, pady=20)

    ttk.Label(url_frame, text="URL:").grid(row=0, column=0, padx=5)
    app.url_var = tk.StringVar(value="http://")
    url_entry = ttk.Entry(url_frame, textvariable=app.url_var, width=40)
    url_entry.grid(row=0, column=1, padx=5, pady=5)

    open_url_btn = ttk.Button(url_frame, text="打开", command=app.open_custom_url)
    open_url_btn.grid(row=0, column=2, padx=5)

