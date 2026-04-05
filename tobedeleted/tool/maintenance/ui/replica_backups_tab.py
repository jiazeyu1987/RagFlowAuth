from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from tool.maintenance.core.constants import PROD_SERVER_IP, TEST_SERVER_IP


def build_replica_backups_tab(app) -> None:
    """Build tab for managing server-local backups under /opt/ragflowauth/data/backups on TEST+PROD."""
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  共享备份  ")

    title = ttk.Label(tab, text="服务器本地备份（/opt/ragflowauth/data/backups）", font=("Arial", 14, "bold"))
    title.pack(pady=10)

    desc = ttk.Label(
        tab,
        text=(
            "说明：此页签分别查看/删除两台服务器本机磁盘上的备份目录（/opt/ragflowauth/data/backups）。\n"
            f"- 测试服务器：{TEST_SERVER_IP}\n"
            f"- 正式服务器：{PROD_SERVER_IP}\n"
            "注意：这里不是 Windows 共享（/mnt/replica）；删除仅影响对应服务器本地备份目录，请谨慎操作。"
        ),
        foreground="gray",
        justify=tk.LEFT,
    )
    desc.pack(padx=20, pady=(0, 10), anchor=tk.W)

    toolbar = ttk.Frame(tab)
    toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))
    ttk.Button(toolbar, text="刷新（两台服务器）", command=app.refresh_replica_backups).pack(side=tk.LEFT, padx=5)

    app.replica_status = ttk.Label(tab, text="点击刷新加载列表", relief=tk.SUNKEN)
    app.replica_status.pack(fill=tk.X, padx=20, pady=(0, 10))

    paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

    # TEST
    test_frame = ttk.LabelFrame(paned, text=f"测试服务器：{TEST_SERVER_IP}")
    paned.add(test_frame, weight=1)

    test_toolbar = ttk.Frame(test_frame)
    test_toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))
    app.test_replica_count = ttk.Label(test_toolbar, text="0 个")
    app.test_replica_count.pack(side=tk.LEFT)
    ttk.Button(test_toolbar, text="删除选中", command=lambda: app.delete_selected_replica_backup("test")).pack(
        side=tk.RIGHT, padx=4
    )

    test_cols = ("name",)
    app.test_replica_tree = ttk.Treeview(test_frame, columns=test_cols, show="headings", selectmode="extended", height=14)
    app.test_replica_tree.heading("name", text="备份目录")
    app.test_replica_tree.column("name", width=520, anchor=tk.W)
    test_scroll = ttk.Scrollbar(test_frame, orient=tk.VERTICAL, command=app.test_replica_tree.yview)
    app.test_replica_tree.configure(yscrollcommand=test_scroll.set)
    app.test_replica_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
    test_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))

    # PROD
    prod_frame = ttk.LabelFrame(paned, text=f"正式服务器：{PROD_SERVER_IP}")
    paned.add(prod_frame, weight=1)

    prod_toolbar = ttk.Frame(prod_frame)
    prod_toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))
    app.prod_replica_count = ttk.Label(prod_toolbar, text="0 个")
    app.prod_replica_count.pack(side=tk.LEFT)
    ttk.Button(prod_toolbar, text="删除选中", command=lambda: app.delete_selected_replica_backup("prod")).pack(
        side=tk.RIGHT, padx=4
    )

    prod_cols = ("name",)
    app.prod_replica_tree = ttk.Treeview(prod_frame, columns=prod_cols, show="headings", selectmode="extended", height=14)
    app.prod_replica_tree.heading("name", text="备份目录")
    app.prod_replica_tree.column("name", width=520, anchor=tk.W)
    prod_scroll = ttk.Scrollbar(prod_frame, orient=tk.VERTICAL, command=app.prod_replica_tree.yview)
    app.prod_replica_tree.configure(yscrollcommand=prod_scroll.set)
    app.prod_replica_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
    prod_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))

    # Load initially
    app.root.after(0, app.refresh_replica_backups)
