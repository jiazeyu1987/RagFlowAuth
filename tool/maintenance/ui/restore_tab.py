from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext

from tool.maintenance.core.constants import TEST_SERVER_IP


def build_restore_tab(app) -> None:
    """Build the '数据还原' tab UI. Restore MUST target the TEST server."""
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  数据还原  ")

    title_label = ttk.Label(tab, text="数据还原", font=("Arial", 14, "bold"))
    title_label.pack(pady=20)

    info_label = ttk.Label(
        tab,
        text=(
            "⚠️ 注意：本页签【只会还原到测试服务器】（不会影响正式服务器）\n"
            f"目标服务器：{TEST_SERVER_IP}\n"
            "本机固定目录：D:\\datas\\RagflowAuth\n"
            "还原内容：auth.db + volumes；若存在 images.tar 也会还原镜像"
        ),
        foreground="gray",
        justify=tk.CENTER,
    )
    info_label.pack(pady=10)

    folder_frame = ttk.LabelFrame(tab, text="选择本地备份（固定目录：D:\\datas\\RagflowAuth）", padding=10)
    folder_frame.pack(fill=tk.BOTH, expand=False, padx=20, pady=10)

    toolbar = ttk.Frame(folder_frame)
    toolbar.pack(fill=tk.X, pady=(0, 8))
    ttk.Button(toolbar, text="刷新列表", command=app.refresh_local_restore_list).pack(side=tk.LEFT, padx=5)
    app.restore_start_btn = ttk.Button(toolbar, text="开始还原", command=app.restore_data, state=tk.DISABLED, width=12)
    app.restore_start_btn.pack(side=tk.LEFT, padx=5)

    columns = ("label", "has_images", "folder")
    app.restore_tree = ttk.Treeview(folder_frame, columns=columns, show="headings", height=6, selectmode="browse")
    app.restore_tree.heading("label", text="备份时间")
    app.restore_tree.heading("has_images", text="有镜像")
    app.restore_tree.heading("folder", text="文件夹")
    app.restore_tree.column("label", width=160, anchor=tk.W)
    app.restore_tree.column("has_images", width=80, anchor=tk.CENTER)
    app.restore_tree.column("folder", width=440, anchor=tk.W)
    app.restore_tree.pack(fill=tk.X, expand=False)
    app.restore_tree.bind("<<TreeviewSelect>>", app.on_restore_backup_selected)

    app.restore_backup_map = {}

    app.restore_info_label = ttk.Label(folder_frame, text="", foreground="blue", justify=tk.LEFT)
    app.restore_info_label.pack(anchor=tk.W, padx=10, pady=5)

    progress_frame = ttk.LabelFrame(tab, text="还原进度", padding=10)
    progress_frame.pack(fill=tk.X, padx=20, pady=10)

    app.restore_progress = ttk.Progressbar(progress_frame, mode="indeterminate", length=400)
    app.restore_progress.pack(pady=5)

    app.restore_status_label = ttk.Label(progress_frame, text="", foreground="gray")
    app.restore_status_label.pack(pady=5)

    restore_btn_frame = ttk.Frame(tab)
    restore_btn_frame.pack(pady=10)

    app.restore_btn = ttk.Button(
        restore_btn_frame,
        text="开始还原数据",
        command=app.restore_data,
        state=tk.DISABLED,
        width=20,
    )
    app.restore_btn.pack()

    output_frame = ttk.LabelFrame(tab, text="还原日志", padding=5)
    output_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

    app.restore_output = scrolledtext.ScrolledText(
        output_frame,
        height=15,
        width=80,
        state=tk.DISABLED,
        font=("Consolas", 9),
    )
    app.restore_output.pack(fill=tk.BOTH, expand=True)

    app.restore_images_exists = False
    app.restore_volumes_exists = False
    app.selected_restore_folder = None
    app.restore_target_ip = TEST_SERVER_IP
    app.restore_target_user = "root"
    app.root.after(0, app.refresh_local_restore_list)

