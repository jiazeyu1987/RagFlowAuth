#!/usr/bin/env python3
from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, PROD_SERVER_IP, TEST_SERVER_IP
from tool.maintenance.core.logging_setup import log_to_file
from tool.maintenance.features.local_backup_catalog import BackupCatalogEntry, list_local_backups
from tool.maintenance.features.local_backup_restore import (
    default_local_auth_db_path,
    restore_downloaded_backup_to_local,
)
from tool.maintenance.features.server_backup_pull import (
    DEFAULT_LOCAL_SAVE_DIR,
    ServerBackupDownloadResult,
    ServerBackupEntry,
    ServerBackupListResult,
    download_server_backup_dir,
    list_server_backup_dirs,
)

SERVER_CHOICES = (
    ("正式服务器", PROD_SERVER_IP),
    ("测试服务器", TEST_SERVER_IP),
)

RESULT_MESSAGES = {
    "ssh_not_found": "本机未找到 ssh 命令。",
    "scp_not_found": "本机未找到 scp 命令。",
    "list_failed": "读取服务器备份列表失败。",
    "no_backups_found": "服务器上没有可识别的备份目录。",
    "invalid_name": "所选备份目录名无效。",
    "destination_root_not_directory": "保存路径不是目录。",
    "destination_root_create_failed": "无法创建保存目录。",
    "destination_exists": "目标目录已存在同名备份，请先清理旧目录或更换保存路径。",
    "remote_backup_missing": "服务器上不存在所选备份目录。",
    "scp_failed": "SCP 拉取失败。",
    "downloaded_dir_missing": "拉取完成后未找到下载目录。",
    "local_move_failed": "移动备份到本地目录失败。",
    "downloaded": "备份拉取完成。",
    "backup_dir_missing": "所选本地备份目录不存在，请先拉取到本地。",
    "backup_auth_db_missing": "备份目录缺少 auth.db，无法执行本地恢复。",
    "local_auth_db_missing": "当前仓库 data/auth.db 不存在，无法执行本地恢复。",
    "local_backend_running": "检测到本地 RagflowAuth 后端仍在 127.0.0.1:8001 运行，请先停止后再恢复。",
    "docker_not_found": "本机未找到 docker 命令，无法恢复本地 RAGFlow volumes。",
    "docker_unavailable": "本机 Docker Engine 不可用，无法恢复本地 RAGFlow volumes。",
    "docker_volume_list_failed": "读取本机 Docker volume 列表失败。",
    "docker_container_query_failed": "查询占用目标 volume 的本机容器失败。",
    "container_stop_failed": "停止占用目标 volume 的本机容器失败。",
    "local_auth_db_copy_failed": "覆盖本地 data/auth.db 失败。",
    "volume_mapping_missing": "至少有一个备份 volume 无法映射到本机 Docker volume。",
    "volume_mapping_ambiguous": "至少有一个备份 volume 映射到了多个本机 Docker volume，无法安全恢复。",
    "volume_restore_failed": "恢复本机 Docker volume 失败。",
    "container_restart_failed": "恢复后重启本机 Docker 容器失败，请手工检查 Docker 状态。",
    "restored": "本地恢复完成。",
}


class ServerBackupPullTool:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RagflowAuth 服务器备份拉取与本地恢复工具")
        self.root.geometry("1180x760")
        self.root.minsize(980, 620)

        self.server_items = [self._format_server_choice(label, ip) for label, ip in SERVER_CHOICES]
        self.server_map = {
            self._format_server_choice(label, ip): {"label": label, "ip": ip}
            for label, ip in SERVER_CHOICES
        }
        self.server_var = tk.StringVar(value=self.server_items[0])
        self.save_path_var = tk.StringVar(value=str(DEFAULT_LOCAL_SAVE_DIR))
        self.status_var = tk.StringVar(value="请选择服务器并加载备份列表；恢复前请先把备份拉取到本地。")
        self.selected_remote_var = tk.StringVar(value="服务器列表：未选择")
        self.selected_local_var = tk.StringVar(value="本地列表：未选择")

        self.remote_backup_rows: dict[str, ServerBackupEntry] = {}
        self.local_backup_rows: dict[str, BackupCatalogEntry] = {}
        self._busy = False

        self._build_ui()
        self.refresh_local_backups(notify_empty=False)

    @staticmethod
    def _format_server_choice(label: str, ip: str) -> str:
        return f"{label} ({ip})"

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 16))

        ttk.Label(
            header,
            text="服务器备份拉取与本地恢复",
            font=("Microsoft YaHei UI", 16, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            header,
            text="正确流程：先从服务器拉取到本地，再从本地备份列表里选择一个执行恢复。",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(6, 0))

        controls = ttk.LabelFrame(container, text="服务器与本地目录")
        controls.pack(fill=tk.X, pady=(0, 16))

        ttk.Label(controls, text="服务器").grid(row=0, column=0, padx=(12, 8), pady=12, sticky="w")
        self.server_combo = ttk.Combobox(
            controls,
            textvariable=self.server_var,
            values=self.server_items,
            state="readonly",
            width=34,
        )
        self.server_combo.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="we")

        self.load_button = ttk.Button(controls, text="加载服务器备份列表", command=self.load_backups)
        self.load_button.grid(row=0, column=2, padx=(0, 12), pady=12, sticky="e")

        ttk.Label(controls, text="保存到").grid(row=1, column=0, padx=(12, 8), pady=(0, 12), sticky="w")
        self.path_entry = ttk.Entry(controls, textvariable=self.save_path_var)
        self.path_entry.grid(row=1, column=1, padx=(0, 12), pady=(0, 12), sticky="we")

        self.browse_button = ttk.Button(controls, text="选择目录", command=self.choose_save_path)
        self.browse_button.grid(row=1, column=2, padx=(0, 12), pady=(0, 12), sticky="e")

        self.refresh_local_button = ttk.Button(controls, text="刷新本地列表", command=self.refresh_local_backups)
        self.refresh_local_button.grid(row=1, column=3, padx=(0, 12), pady=(0, 12), sticky="e")

        controls.columnconfigure(1, weight=1)

        lists = ttk.Frame(container)
        lists.pack(fill=tk.BOTH, expand=True)
        lists.columnconfigure(0, weight=1)
        lists.columnconfigure(1, weight=1)
        lists.rowconfigure(0, weight=1)

        remote_frame = ttk.LabelFrame(lists, text="服务器备份列表")
        remote_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        remote_frame.columnconfigure(0, weight=1)
        remote_frame.rowconfigure(0, weight=1)

        remote_columns = ("backup_type", "raw_name")
        self.remote_tree = ttk.Treeview(
            remote_frame,
            columns=remote_columns,
            show="tree headings",
            selectmode="browse",
        )
        self.remote_tree.heading("#0", text="日期名称")
        self.remote_tree.heading("backup_type", text="类型")
        self.remote_tree.heading("raw_name", text="原始目录名")
        self.remote_tree.column("#0", width=220, anchor="w")
        self.remote_tree.column("backup_type", width=120, anchor="center")
        self.remote_tree.column("raw_name", width=320, anchor="w")
        self.remote_tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        self.remote_tree.bind("<<TreeviewSelect>>", self._on_remote_backup_selected)

        remote_scroll = ttk.Scrollbar(remote_frame, orient=tk.VERTICAL, command=self.remote_tree.yview)
        remote_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.remote_tree.configure(yscrollcommand=remote_scroll.set)

        local_frame = ttk.LabelFrame(lists, text="本地备份列表")
        local_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        local_frame.columnconfigure(0, weight=1)
        local_frame.rowconfigure(0, weight=1)

        local_columns = ("folder_name", "local_path")
        self.local_tree = ttk.Treeview(
            local_frame,
            columns=local_columns,
            show="tree headings",
            selectmode="browse",
        )
        self.local_tree.heading("#0", text="日期名称")
        self.local_tree.heading("folder_name", text="目录名")
        self.local_tree.heading("local_path", text="本地路径")
        self.local_tree.column("#0", width=220, anchor="w")
        self.local_tree.column("folder_name", width=220, anchor="w")
        self.local_tree.column("local_path", width=420, anchor="w")
        self.local_tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        self.local_tree.bind("<<TreeviewSelect>>", self._on_local_backup_selected)

        local_scroll = ttk.Scrollbar(local_frame, orient=tk.VERTICAL, command=self.local_tree.yview)
        local_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.local_tree.configure(yscrollcommand=local_scroll.set)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(12, 8))

        selection_info = ttk.Frame(actions)
        selection_info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(selection_info, textvariable=self.selected_remote_var).pack(anchor=tk.W)
        ttk.Label(selection_info, textvariable=self.selected_local_var).pack(anchor=tk.W, pady=(4, 0))

        button_group = ttk.Frame(actions)
        button_group.pack(side=tk.RIGHT)

        self.restore_button = ttk.Button(button_group, text="从本地列表恢复", command=self.restore_selected_backup)
        self.restore_button.pack(side=tk.RIGHT, padx=(8, 0))

        self.pull_button = ttk.Button(button_group, text="拉取所选服务器备份", command=self.pull_selected_backup)
        self.pull_button.pack(side=tk.RIGHT)

        ttk.Label(
            container,
            text=f"本地恢复目标 auth.db：{default_local_auth_db_path()}",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(container, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w").pack(fill=tk.X)

    def _set_busy(self, busy: bool, status_text: str | None = None) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        combo_state = tk.DISABLED if busy else "readonly"

        self.server_combo.configure(state=combo_state)
        self.path_entry.configure(state=state)
        self.load_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.refresh_local_button.configure(state=state)
        self.pull_button.configure(state=state)
        self.restore_button.configure(state=state)

        if status_text is not None:
            self.status_var.set(status_text)

    def _selected_server(self) -> tuple[str, str]:
        current = self.server_var.get()
        server = self.server_map[current]
        return server["label"], server["ip"]

    def _selected_remote_backup(self) -> ServerBackupEntry | None:
        selection = self.remote_tree.selection()
        if not selection:
            return None
        return self.remote_backup_rows.get(selection[0])

    def _selected_local_backup(self) -> BackupCatalogEntry | None:
        selection = self.local_tree.selection()
        if not selection:
            return None
        return self.local_backup_rows.get(selection[0])

    def _result_message(self, code: str, raw: str) -> str:
        if code.startswith("volume_mapping_missing:"):
            _, volume_name = code.split(":", 1)
            return f"{RESULT_MESSAGES['volume_mapping_missing']}\n\n备份 volume：{volume_name}"
        if code.startswith("volume_mapping_ambiguous:"):
            _, volume_name, candidates = code.split(":", 2)
            return (
                f"{RESULT_MESSAGES['volume_mapping_ambiguous']}\n\n"
                f"备份 volume：{volume_name}\n本机候选 volume：{candidates}"
            )

        message = RESULT_MESSAGES.get(code, code)
        details = (raw or "").strip()
        return f"{message}\n\n{details}" if details else message

    def _start_background(self, *, busy_text: str, work, on_done) -> None:
        if self._busy:
            return

        self._set_busy(True, busy_text)

        def runner() -> None:
            try:
                payload = work()
            except Exception as exc:  # pragma: no cover
                log_to_file(f"[ServerBackupPullTool] unexpected error: {exc}", "ERROR")
                self.root.after(0, lambda: self._on_background_failure(str(exc)))
                return
            self.root.after(0, lambda: on_done(payload))

        threading.Thread(target=runner, daemon=True).start()

    def _on_background_failure(self, message: str) -> None:
        self._set_busy(False, "执行失败，请查看错误提示。")
        messagebox.showerror("执行失败", message)

    def _clear_remote_backups(self) -> None:
        self.remote_backup_rows.clear()
        for item in self.remote_tree.get_children():
            self.remote_tree.delete(item)

    def _clear_local_backups(self) -> None:
        self.local_backup_rows.clear()
        for item in self.local_tree.get_children():
            self.local_tree.delete(item)

    def _refresh_remote_selection_hint(self) -> None:
        entry = self._selected_remote_backup()
        if entry is None:
            self.selected_remote_var.set("服务器列表：未选择")
            return
        self.selected_remote_var.set(f"服务器列表：{entry.created_at} | {entry.backup_type} | {entry.name}")

    def _refresh_local_selection_hint(self) -> None:
        entry = self._selected_local_backup()
        if entry is None:
            self.selected_local_var.set("本地列表：未选择")
            return
        self.selected_local_var.set(f"本地列表：{entry.label} | {entry.path}")

    def choose_save_path(self) -> None:
        current_path = Path(self.save_path_var.get()).expanduser()
        initial_dir = current_path if current_path.exists() else DEFAULT_LOCAL_SAVE_DIR
        chosen = filedialog.askdirectory(
            parent=self.root,
            title="选择本地保存目录",
            initialdir=str(initial_dir),
            mustexist=False,
        )
        if not chosen:
            return

        self.save_path_var.set(chosen)
        self.refresh_local_backups(notify_empty=True)

    def load_backups(self) -> None:
        _, server_ip = self._selected_server()
        self._start_background(
            busy_text=f"正在读取 {server_ip} 的服务器备份列表...",
            work=lambda: list_server_backup_dirs(server_ip=server_ip, server_user=DEFAULT_SERVER_USER),
            on_done=self._finish_load_backups,
        )

    def _finish_load_backups(self, result: ServerBackupListResult) -> None:
        self._set_busy(False)
        self._clear_remote_backups()

        if not result.ok:
            message = self._result_message(result.message, result.raw)
            self.status_var.set(message.splitlines()[0])
            self.selected_remote_var.set("服务器列表：未选择")
            messagebox.showerror("加载服务器备份列表失败", message)
            return

        for index, entry in enumerate(result.backups, start=1):
            item_id = f"remote-{index}"
            self.remote_backup_rows[item_id] = entry
            self.remote_tree.insert(
                "",
                tk.END,
                iid=item_id,
                text=entry.created_at,
                values=(entry.backup_type, entry.name),
            )

        server_label, server_ip = self._selected_server()
        self.status_var.set(f"{server_label} {server_ip} 共加载 {len(result.backups)} 个服务器备份。")
        self.selected_remote_var.set("服务器列表：未选择")

    def refresh_local_backups(
        self,
        *,
        notify_empty: bool = True,
        preferred_name: str | None = None,
        status_override: str | None = None,
    ) -> None:
        current_entry = self._selected_local_backup()
        if preferred_name is None and current_entry is not None:
            preferred_name = current_entry.path.name

        self._clear_local_backups()

        save_path_text = self.save_path_var.get().strip()
        if not save_path_text:
            self.selected_local_var.set("本地列表：未选择")
            self.status_var.set("请先选择本地保存目录。")
            return

        root_dir = Path(save_path_text).expanduser()
        if not root_dir.exists():
            self.selected_local_var.set("本地列表：未选择")
            self.status_var.set(f"本地目录不存在：{root_dir}")
            return
        if not root_dir.is_dir():
            self.selected_local_var.set("本地列表：未选择")
            self.status_var.set(f"本地路径不是目录：{root_dir}")
            return

        backups = list_local_backups(root_dir)
        selected_item_id: str | None = None

        for index, entry in enumerate(backups, start=1):
            item_id = f"local-{index}"
            self.local_backup_rows[item_id] = entry
            self.local_tree.insert(
                "",
                tk.END,
                iid=item_id,
                text=entry.label,
                values=(entry.path.name, str(entry.path)),
            )
            if preferred_name and entry.path.name == preferred_name:
                selected_item_id = item_id

        if selected_item_id is not None:
            self.local_tree.selection_set(selected_item_id)
            self.local_tree.focus(selected_item_id)
            self.local_tree.see(selected_item_id)

        self._refresh_local_selection_hint()

        if status_override is not None:
            self.status_var.set(status_override)
            return

        if backups:
            self.status_var.set(f"本地目录共加载 {len(backups)} 个可恢复备份：{root_dir}")
        elif notify_empty:
            self.status_var.set(f"本地目录中暂无可恢复备份：{root_dir}")
        else:
            self.status_var.set(f"等待从服务器拉取备份到本地目录：{root_dir}")

    def _on_remote_backup_selected(self, _event=None) -> None:
        self._refresh_remote_selection_hint()

    def _on_local_backup_selected(self, _event=None) -> None:
        self._refresh_local_selection_hint()

    def pull_selected_backup(self) -> None:
        entry = self._selected_remote_backup()
        if entry is None:
            messagebox.showwarning("未选择服务器备份", "请先从服务器备份列表中选择一个备份。")
            return

        save_path = self.save_path_var.get().strip()
        if not save_path:
            messagebox.showwarning("缺少保存路径", "请先选择本地保存目录。")
            return

        _, server_ip = self._selected_server()
        self._start_background(
            busy_text=f"正在拉取服务器备份 {entry.name}...",
            work=lambda: download_server_backup_dir(
                server_ip=server_ip,
                server_user=DEFAULT_SERVER_USER,
                name=entry.name,
                destination_root=save_path,
            ),
            on_done=self._finish_pull_backup,
        )

    def _finish_pull_backup(self, result: ServerBackupDownloadResult) -> None:
        self._set_busy(False)

        if not result.ok:
            message = self._result_message(result.message, result.raw)
            self.status_var.set(message.splitlines()[0])
            messagebox.showerror("拉取备份失败", message)
            return

        self.refresh_local_backups(
            notify_empty=True,
            preferred_name=result.name,
            status_override=f"拉取完成，已保存到：{result.destination}；本地列表已刷新。",
        )
        messagebox.showinfo("拉取完成", f"备份已拉取到：\n{result.destination}")

    def restore_selected_backup(self) -> None:
        entry = self._selected_local_backup()
        if entry is None:
            messagebox.showwarning("未选择本地备份", "请先从本地备份列表中选择一个备份。")
            return

        confirm_message = (
            f"将从以下本地备份执行恢复：\n{entry.path}\n\n"
            f"这会覆盖当前仓库的本地数据库：\n{default_local_auth_db_path()}\n\n"
            "如果备份中包含 volumes/*.tar.gz，还会恢复到本机匹配到的 Docker volumes，"
            "并在过程中停止/重启相关本机容器。\n\n"
            "执行前请确认本地 RagflowAuth 后端已经停止。是否继续？"
        )
        if not messagebox.askyesno("确认本地恢复", confirm_message):
            return

        self._start_background(
            busy_text=f"正在从本地备份 {entry.path.name} 恢复...",
            work=lambda: restore_downloaded_backup_to_local(backup_dir=entry.path),
            on_done=self._finish_restore_backup,
        )

    def _finish_restore_backup(self, result) -> None:
        self._set_busy(False)

        if not result.ok:
            message = self._result_message(result.message, result.raw)
            self.status_var.set(message.splitlines()[0])
            messagebox.showerror("本地恢复失败", message)
            return

        restored_volumes = "、".join(result.restored_volume_names) if result.restored_volume_names else "无"
        restarted = "、".join(result.stopped_container_names) if result.stopped_container_names else "无"
        self.status_var.set(f"本地恢复完成：{result.restored_auth_db_path}")
        messagebox.showinfo(
            "本地恢复完成",
            (
                f"auth.db 已恢复到：\n{result.restored_auth_db_path}\n\n"
                f"恢复的本机 Docker volumes：{restored_volumes}\n"
                f"处理过的本机容器：{restarted}"
            ),
        )


def main() -> None:
    root = tk.Tk()
    try:
        root.state("zoomed")
    except Exception:
        pass
    ServerBackupPullTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
