from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_backup_files_tab(app) -> None:
    """Build the '备份文件' tab UI. Data loading/deleting happens in tool.py callbacks."""
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  备份文件  ")

    title_label = ttk.Label(tab, text="服务器备份文件管理", font=("Arial", 14, "bold"))
    title_label.pack(pady=10)

    desc_label = ttk.Label(
        tab,
        text="管理服务器上的备份文件，支持查看和删除两个位置的备份：\n"
        "• /opt/ragflowauth/data/backups/ - 主要存储 auth.db\n"
        "• /opt/ragflowauth/backups/ - 主要存储 volumes/*.tar.gz",
        foreground="gray",
        justify=tk.LEFT,
    )
    desc_label.pack(pady=(0, 10), padx=20)

    button_frame = ttk.Frame(tab)
    button_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

    ttk.Button(button_frame, text="刷新文件列表", command=app.refresh_backup_files).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="删除选中文件", command=app.delete_selected_backup_files).pack(side=tk.LEFT, padx=5)

    app.backup_keep_days_var = tk.StringVar(value="30")
    ttk.Label(button_frame, text="保留天数:").pack(side=tk.LEFT, padx=(12, 2))
    ttk.Entry(button_frame, textvariable=app.backup_keep_days_var, width=5).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(button_frame, text="清理旧备份", command=app.cleanup_old_backups).pack(side=tk.LEFT, padx=5)

    paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

    left_frame = ttk.LabelFrame(paned, text="/opt/ragflowauth/data/backups/ (auth.db)")
    paned.add(left_frame, weight=1)

    left_columns = ("name", "size", "date")
    app.left_tree = ttk.Treeview(left_frame, columns=left_columns, show="tree headings", selectmode="extended")
    app.left_tree.heading("#0", text="文件名")
    app.left_tree.heading("size", text="大小")
    app.left_tree.heading("date", text="日期")

    app.left_tree.column("#0", width=250)
    app.left_tree.column("size", width=100)
    app.left_tree.column("date", width=150)

    left_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=app.left_tree.yview)
    app.left_tree.configure(yscrollcommand=left_scrollbar.set)

    app.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app.left_tree.bind("<Double-1>", lambda _: app.show_backup_file_details("left"))

    right_frame = ttk.LabelFrame(paned, text="/opt/ragflowauth/backups/ (volumes)")
    paned.add(right_frame, weight=1)

    right_columns = ("name", "size", "date")
    app.right_tree = ttk.Treeview(right_frame, columns=right_columns, show="tree headings", selectmode="extended")
    app.right_tree.heading("#0", text="文件名")
    app.right_tree.heading("size", text="大小")
    app.right_tree.heading("date", text="日期")

    app.right_tree.column("#0", width=250)
    app.right_tree.column("size", width=100)
    app.right_tree.column("date", width=150)

    right_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=app.right_tree.yview)
    app.right_tree.configure(yscrollcommand=right_scrollbar.set)

    app.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app.right_tree.bind("<Double-1>", lambda _: app.show_backup_file_details("right"))

    app.backup_files_status = ttk.Label(tab, text="点击'刷新文件列表'加载数据", relief=tk.SUNKEN)
    app.backup_files_status.pack(fill=tk.X, padx=20, pady=(0, 10))

