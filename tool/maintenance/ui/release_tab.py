from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext

from tool.maintenance.core.constants import PROD_SERVER_IP, TEST_SERVER_IP


def build_release_tab(app) -> None:
    """
    Build the "发布" tab and its 3 sub-tabs.

    This function mutates `app` by attaching widget references used by existing callbacks.
    The callback implementations remain on the RagflowAuthTool instance (app).
    """
    tab = ttk.Frame(app.notebook)
    app.notebook.add(tab, text="  发布  ")

    title = ttk.Label(tab, text="发布到生产（测试 -> 正式）", font=("Arial", 14, "bold"))
    title.pack(pady=10)

    version_frame = ttk.Frame(tab)
    version_frame.pack(fill=tk.X, padx=20, pady=(0, 8))
    ttk.Label(version_frame, text="版本号（留空自动生成）").pack(side=tk.LEFT)
    app.release_version_var = tk.StringVar(value="")
    ttk.Entry(version_frame, textvariable=app.release_version_var, width=28).pack(side=tk.LEFT, padx=6)
    ttk.Button(version_frame, text="生成版本号", command=app._release_generate_version).pack(side=tk.LEFT, padx=6)

    desc = ttk.Label(
        tab,
        text=(
            "本页包含三个发布流：\n"
            f"- 本机 -> 测试：把本机构建的镜像发布到测试服务器 {TEST_SERVER_IP}\n"
            f"- 测试 -> 正式（镜像）：把测试服务器当前运行的镜像发布到正式服务器 {PROD_SERVER_IP}\n"
            f"- 测试 -> 正式（数据）：把测试服务器数据同步到正式服务器 {PROD_SERVER_IP}\n"
        ),
        foreground="gray",
        justify=tk.LEFT,
    )
    desc.pack(pady=(0, 10), padx=20, anchor=tk.W)

    # Sub-tabs (make them visually distinct and easier to click)
    try:
        style = ttk.Style()
        style.configure("Release.TNotebook.Tab", font=("Arial", 14, "bold"), padding=(22, 12))
    except Exception:
        pass

    app.release_notebook = ttk.Notebook(tab, style="Release.TNotebook")
    app.release_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    _create_release_local_to_test_tab(app)
    _create_release_test_to_prod_tab(app)
    _create_release_test_data_to_prod_tab(app)
    _create_release_history_tab(app)

    # Defer initial refresh until after the UI is fully initialized (status_bar created).
    app.root.after(0, app.refresh_release_versions)
    app.root.after(0, app.refresh_release_history)


def _create_release_local_to_test_tab(app) -> None:
    tab = ttk.Frame(app.release_notebook)
    app.release_notebook.add(tab, text="① 本机 → 测试")

    button_frame = ttk.Frame(tab)
    button_frame.pack(fill=tk.X, padx=20, pady=(10, 10))
    ttk.Button(button_frame, text="刷新测试版本", command=app.refresh_release_test_versions).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="发布本机到测试", command=app.publish_local_to_test).pack(side=tk.LEFT, padx=5)

    info_frame = ttk.Frame(tab)
    info_frame.pack(fill=tk.BOTH, expand=False, padx=20, pady=(0, 10))
    before = ttk.LabelFrame(info_frame, text=f"测试发布前版本 ({TEST_SERVER_IP})", padding=10)
    after = ttk.LabelFrame(info_frame, text=f"测试发布后版本 ({TEST_SERVER_IP})", padding=10)
    before.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
    after.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    app.release_test_before_text = scrolledtext.ScrolledText(before, height=10, width=60)
    app.release_test_before_text.pack(fill=tk.BOTH, expand=True)
    app.release_test_after_text = scrolledtext.ScrolledText(after, height=10, width=60)
    app.release_test_after_text.pack(fill=tk.BOTH, expand=True)

    log_frame = ttk.LabelFrame(tab, text="发布日志（本机 -> 测试）", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
    app.release_local_log_text = scrolledtext.ScrolledText(log_frame, height=18)
    app.release_local_log_text.pack(fill=tk.BOTH, expand=True)


def _create_release_test_to_prod_tab(app) -> None:
    tab = ttk.Frame(app.release_notebook)
    app.release_notebook.add(tab, text="② 测试 → 正式（镜像）")

    button_frame = ttk.Frame(tab)
    button_frame.pack(fill=tk.X, padx=20, pady=(10, 10))
    ttk.Button(button_frame, text="刷新版本信息", command=app.refresh_release_versions).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="从测试发布到正式", command=app.publish_test_to_prod).pack(side=tk.LEFT, padx=5)
    app.release_include_ragflow_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(button_frame, text="同步 RAGFlow 镜像", variable=app.release_include_ragflow_var).pack(
        side=tk.LEFT, padx=(10, 0)
    )

    rollback_frame = ttk.LabelFrame(tab, text=f"版本回滚（正式 {PROD_SERVER_IP}）", padding=10)
    rollback_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

    row = ttk.Frame(rollback_frame)
    row.pack(fill=tk.X)
    ttk.Label(row, text="选择版本:").pack(side=tk.LEFT)
    app.rollback_version_var = tk.StringVar(value="")
    app.rollback_version_combo = ttk.Combobox(row, textvariable=app.rollback_version_var, width=28, state="readonly")
    app.rollback_version_combo.pack(side=tk.LEFT, padx=6)
    ttk.Button(row, text="刷新可回滚版本", command=app.refresh_prod_rollback_versions).pack(side=tk.LEFT, padx=6)
    ttk.Button(row, text="回滚到此版本", command=app.rollback_prod_to_selected_version).pack(side=tk.LEFT, padx=6)

    info_frame = ttk.Frame(tab)
    info_frame.pack(fill=tk.BOTH, expand=False, padx=20, pady=(0, 10))

    left = ttk.LabelFrame(info_frame, text=f"测试版本信息 ({TEST_SERVER_IP})", padding=10)
    right = ttk.LabelFrame(info_frame, text=f"正式版本信息 ({PROD_SERVER_IP})", padding=10)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    app.release_test_text = scrolledtext.ScrolledText(left, height=10, width=60)
    app.release_test_text.pack(fill=tk.BOTH, expand=True)
    app.release_prod_text = scrolledtext.ScrolledText(right, height=10, width=60)
    app.release_prod_text.pack(fill=tk.BOTH, expand=True)

    log_frame = ttk.LabelFrame(tab, text="发布日志（测试 -> 正式）", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
    app.release_log_text = scrolledtext.ScrolledText(log_frame, height=18)
    app.release_log_text.pack(fill=tk.BOTH, expand=True)


def _create_release_test_data_to_prod_tab(app) -> None:
    tab = ttk.Frame(app.release_notebook)
    app.release_notebook.add(tab, text="③ 测试 → 正式（数据）")

    desc = ttk.Label(
        tab,
        text=(
            "将【测试服务器】数据同步到【正式服务器】（高风险：覆盖生产数据）：\n"
            f"- 测试: {TEST_SERVER_IP} -> 正式: {PROD_SERVER_IP}\n"
            "- 内容: auth.db + RAGFlow volumes（ragflow_compose_*）\n"
            "- 发布过程中会自动把正式服务器 ragflow_config.json 的 base_url 修正为正式服务器\n"
        ),
        foreground="gray",
        justify=tk.LEFT,
    )
    desc.pack(fill=tk.X, padx=20, pady=(10, 6), anchor=tk.W)

    button_frame = ttk.Frame(tab)
    button_frame.pack(fill=tk.X, padx=20, pady=(6, 10))
    ttk.Button(button_frame, text="从测试发布数据到正式", command=app.publish_test_data_to_prod).pack(
        side=tk.LEFT, padx=5
    )

    log_frame = ttk.LabelFrame(tab, text="发布日志（测试数据 -> 正式）", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
    app.release_data_log_text = scrolledtext.ScrolledText(log_frame, height=18)
    app.release_data_log_text.pack(fill=tk.BOTH, expand=True)


def _create_release_history_tab(app) -> None:
    tab = ttk.Frame(app.release_notebook)
    app.release_notebook.add(tab, text="发布记录")

    button_frame = ttk.Frame(tab)
    button_frame.pack(fill=tk.X, padx=20, pady=(10, 10))
    ttk.Button(button_frame, text="刷新发布记录", command=app.refresh_release_history).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="复制到剪贴板", command=app.copy_release_history_to_clipboard).pack(side=tk.LEFT, padx=5)

    info = ttk.Label(
        tab,
        text="发布/数据同步/回滚成功后，会自动追加到 doc/maintenance/release_history.md",
        foreground="gray",
        justify=tk.LEFT,
    )
    info.pack(fill=tk.X, padx=20, pady=(0, 6), anchor=tk.W)

    box = ttk.LabelFrame(tab, text="发布记录（只读）", padding=10)
    box.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
    app.release_history_text = scrolledtext.ScrolledText(box, height=20)
    app.release_history_text.pack(fill=tk.BOTH, expand=True)
