from __future__ import annotations

import shlex
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


DEFAULT_NAS_IP = "172.30.30.4"
DEFAULT_NAS_SHARE = "Backup"
DEFAULT_NAS_USERNAME = "beifen"
DEFAULT_NAS_PASSWORD = "TYkHwI"
DEFAULT_NAS_MOUNT_POINT = "/mnt/nas"


def build_nas_tab(app) -> None:
    if getattr(app, "nas_tab", None) is not None:
        return
    app.nas_tab = ttk.Frame(app.notebook)
    app.notebook.add(app.nas_tab, text="  NAS云盘  ")
    app.nas_tab_controller = _NasTabController(app, app.nas_tab)


class _NasTabController:
    def __init__(self, app, parent) -> None:
        self.app = app
        self.parent = parent
        self.current_path = DEFAULT_NAS_MOUNT_POINT
        self.history: list[str] = []
        self._build()
        self.load_directory(DEFAULT_NAS_MOUNT_POINT)

    def _build(self) -> None:
        config_frame = ttk.LabelFrame(self.parent, text="NAS 配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.nas_ip_var = tk.StringVar(value=DEFAULT_NAS_IP)
        self.nas_share_var = tk.StringVar(value=DEFAULT_NAS_SHARE)
        self.nas_user_var = tk.StringVar(value=DEFAULT_NAS_USERNAME)
        self.nas_password_var = tk.StringVar(value=DEFAULT_NAS_PASSWORD)
        self.mount_var = tk.BooleanVar(value=True)

        ttk.Label(config_frame, text="NAS 服务器 IP:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6), pady=4)
        ttk.Entry(config_frame, textvariable=self.nas_ip_var, width=16).grid(row=0, column=1, sticky=tk.W, pady=4)
        ttk.Label(config_frame, text="共享文件夹:").grid(row=0, column=2, sticky=tk.W, padx=(16, 6), pady=4)
        ttk.Entry(config_frame, textvariable=self.nas_share_var, width=18).grid(row=0, column=3, sticky=tk.W, pady=4)
        ttk.Label(config_frame, text="访问用户名:").grid(row=0, column=4, sticky=tk.W, padx=(16, 6), pady=4)
        ttk.Entry(config_frame, textvariable=self.nas_user_var, width=14).grid(row=0, column=5, sticky=tk.W, pady=4)
        ttk.Label(config_frame, text="访问密码:").grid(row=0, column=6, sticky=tk.W, padx=(16, 6), pady=4)
        ttk.Entry(config_frame, textvariable=self.nas_password_var, width=16, show="*").grid(row=0, column=7, sticky=tk.W, pady=4)

        ttk.Checkbutton(config_frame, text="需要协助挂载 CIFS 共享", variable=self.mount_var).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(8, 0)
        )
        ttk.Label(
            config_frame,
            text=f"默认挂载点: {DEFAULT_NAS_MOUNT_POINT}，仅管理员可见",
            foreground="gray",
        ).grid(row=1, column=3, columnspan=5, sticky=tk.W, pady=(8, 0))

        nav_frame = ttk.Frame(self.parent, padding=8)
        nav_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        ttk.Button(nav_frame, text="挂载并刷新", command=self.mount_and_refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="返回", command=self.go_back, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="上级", command=self.go_up, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="主页", command=self.go_home, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="刷新", command=self.refresh, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Label(nav_frame, text="路径:").pack(side=tk.LEFT, padx=(12, 4))
        self.path_var = tk.StringVar(value=DEFAULT_NAS_MOUNT_POINT)
        path_entry = ttk.Entry(nav_frame, textvariable=self.path_var, width=60)
        path_entry.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        ttk.Button(nav_frame, text="前往", command=self.go_to_path, width=8).pack(side=tk.LEFT, padx=2)

        action_frame = ttk.Frame(self.parent, padding=8)
        action_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Button(action_frame, text="搜索", command=self.search_file, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="统计", command=self.show_stats, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="下载文件", command=self.download_file, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="下载目录", command=self.download_dir, width=12).pack(side=tk.LEFT, padx=2)
        self.count_label = ttk.Label(action_frame, text="", foreground="gray")
        self.count_label.pack(side=tk.RIGHT, padx=4)

        list_frame = ttk.Frame(self.parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("size", "modified", "type")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="名称")
        self.tree.heading("size", text="大小")
        self.tree.heading("modified", text="修改时间")
        self.tree.heading("type", text="类型")
        self.tree.column("#0", width=520, minwidth=220)
        self.tree.column("size", width=120, anchor="e")
        self.tree.column("modified", width=160, anchor="center")
        self.tree.column("type", width=80, anchor="center")
        self.tree.bind("<Double-1>", self.on_double_click)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(self.parent, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        self.status_label.pack(fill=tk.X, padx=10, pady=(0, 10))

    def _remote_exec(self, command: str, timeout: int = 60):
        if not self.app.update_ssh_executor():
            raise RuntimeError("SSH 配置无效，请先检查服务器 IP 和用户名")
        return self.app.ssh_executor.execute(command, timeout_seconds=timeout)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _mount_if_needed(self) -> None:
        if not self.mount_var.get():
            return

        share = self.nas_share_var.get().strip()
        nas_ip = self.nas_ip_var.get().strip()
        nas_user = self.nas_user_var.get().strip()
        nas_password = self.nas_password_var.get().strip()
        mount_point = DEFAULT_NAS_MOUNT_POINT

        unc = f"//{nas_ip}/{share}"
        options = f"username={nas_user},password={nas_password},iocharset=utf8,vers=3.0"
        command = (
            f"mkdir -p {shlex.quote(mount_point)} && "
            f"(mountpoint -q {shlex.quote(mount_point)} || "
            f"mount -t cifs {shlex.quote(unc)} {shlex.quote(mount_point)} -o {shlex.quote(options)})"
        )
        success, output = self._remote_exec(command, timeout=120)
        if not success:
            raise RuntimeError(output.strip() or "挂载 NAS 失败")

    def _load_directory_sync(self, path: str) -> list[dict[str, str | bool]]:
        safe_path = path.strip() or DEFAULT_NAS_MOUNT_POINT
        command = (
            f"test -d {shlex.quote(safe_path)} && "
            f"find {shlex.quote(safe_path)} -mindepth 1 -maxdepth 1 "
            f"-printf '%y\\t%s\\t%TY-%Tm-%Td %TH:%TM\\t%f\\n' | sort"
        )
        success, output = self._remote_exec(command, timeout=90)
        if not success:
            raise RuntimeError(output.strip() or f"读取目录失败: {safe_path}")

        items: list[dict[str, str | bool]] = []
        for line in output.splitlines():
            parts = line.split("\t", 3)
            if len(parts) != 4:
                continue
            item_type, size, modified, name = parts
            is_dir = item_type == "d"
            item_path = f"{safe_path.rstrip('/')}/{name}" if safe_path != "/" else f"/{name}"
            items.append(
                {
                    "name": name,
                    "size": "-" if is_dir else size,
                    "modified": modified,
                    "type": "目录" if is_dir else "文件",
                    "is_dir": is_dir,
                    "path": item_path,
                }
            )
        return items

    def load_directory(self, path: str | None = None) -> None:
        target_path = (path or self.path_var.get().strip() or DEFAULT_NAS_MOUNT_POINT).strip()
        self._set_status(f"加载中: {target_path}")

        def run() -> None:
            try:
                self._mount_if_needed()
                items = self._load_directory_sync(target_path)
                self.app.root.after(0, lambda: self._update_tree(target_path, items))
            except Exception as exc:
                self.app.root.after(0, lambda: messagebox.showerror("NAS 云盘", str(exc)))
                self.app.root.after(0, lambda: self._set_status("加载失败"))

        threading.Thread(target=run, daemon=True).start()

    def _update_tree(self, path: str, items: list[dict[str, str | bool]]) -> None:
        self.tree.delete(*self.tree.get_children())
        self.current_path = path
        self.path_var.set(path)
        if not self.history or self.history[-1] != path:
            self.history.append(path)

        if path not in ("", "/", DEFAULT_NAS_MOUNT_POINT):
            self.tree.insert("", "end", iid="__parent__", text="📂 ..", values=("", "", "上级"))

        dirs = [item for item in items if item["is_dir"]]
        files = [item for item in items if not item["is_dir"]]
        for item in dirs + files:
            icon = "📁" if item["is_dir"] else "📄"
            self.tree.insert(
                "",
                "end",
                iid=str(item["path"]),
                text=f"{icon} {item['name']}",
                values=(item["size"], item["modified"], item["type"]),
            )

        self.count_label.config(text=f"目录 {len(dirs)} 个，文件 {len(files)} 个")
        self._set_status(f"当前路径: {path}")

    def go_back(self) -> None:
        if len(self.history) > 1:
            self.history.pop()
            self.load_directory(self.history[-1])

    def go_up(self) -> None:
        if self.current_path and self.current_path not in ("/", DEFAULT_NAS_MOUNT_POINT):
            parent = str(Path(self.current_path).parent)
            self.history = [parent]
            self.load_directory(parent)

    def go_home(self) -> None:
        self.history = []
        self.load_directory(DEFAULT_NAS_MOUNT_POINT)

    def go_to_path(self) -> None:
        target = self.path_var.get().strip()
        if target:
            self.history = [target]
            self.load_directory(target)

    def refresh(self) -> None:
        self.load_directory(self.current_path)

    def mount_and_refresh(self) -> None:
        self.load_directory(DEFAULT_NAS_MOUNT_POINT)

    def on_double_click(self, _event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        if item_id == "__parent__":
            self.go_up()
            return
        values = self.tree.item(item_id, "values")
        if values and len(values) >= 3 and values[2] == "目录":
            self.load_directory(item_id)

    def _selected_item(self):
        selection = self.tree.selection()
        if not selection:
            return None, None, None
        item_id = selection[0]
        if item_id == "__parent__":
            return None, None, None
        item = self.tree.item(item_id)
        values = item.get("values", ())
        return item_id, item, values

    def search_file(self) -> None:
        dialog = tk.Toplevel(self.parent)
        dialog.title("搜索 NAS 文件")
        dialog.geometry("420x120")
        dialog.transient(self.parent)
        dialog.grab_set()

        ttk.Label(dialog, text="文件名模式(支持 *):").pack(pady=(12, 6))
        entry = ttk.Entry(dialog, width=42)
        entry.insert(0, "*")
        entry.pack(pady=4)

        def do_search() -> None:
            keyword = entry.get().strip()
            if not keyword:
                messagebox.showwarning("NAS 云盘", "请输入搜索条件")
                return
            dialog.destroy()
            self._set_status(f"搜索中: {keyword}")

            def run() -> None:
                try:
                    command = (
                        f"find {shlex.quote(self.current_path)} -name {shlex.quote(keyword)} 2>/dev/null | head -100"
                    )
                    success, output = self._remote_exec(command, timeout=120)
                    if not success:
                        raise RuntimeError(output.strip() or "搜索失败")
                    result = output.strip() or "未找到匹配文件"
                    self.app.root.after(0, lambda: messagebox.showinfo("搜索结果", result))
                    self.app.root.after(0, lambda: self._set_status("搜索完成"))
                except Exception as exc:
                    self.app.root.after(0, lambda: messagebox.showerror("NAS 云盘", str(exc)))
                    self.app.root.after(0, lambda: self._set_status("搜索失败"))

            threading.Thread(target=run, daemon=True).start()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="搜索", command=do_search).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    def show_stats(self) -> None:
        self._set_status("统计中...")

        def run() -> None:
            try:
                total_ok, total = self._remote_exec(f"du -sh {shlex.quote(DEFAULT_NAS_MOUNT_POINT)} 2>/dev/null | cut -f1", timeout=120)
                files_ok, files = self._remote_exec(f"find {shlex.quote(DEFAULT_NAS_MOUNT_POINT)} -type f 2>/dev/null | wc -l", timeout=120)
                dirs_ok, dirs = self._remote_exec(f"find {shlex.quote(DEFAULT_NAS_MOUNT_POINT)} -type d 2>/dev/null | wc -l", timeout=120)
                df_ok, df = self._remote_exec(f"df -h {shlex.quote(DEFAULT_NAS_MOUNT_POINT)} 2>/dev/null", timeout=30)
                if not all((total_ok, files_ok, dirs_ok, df_ok)):
                    raise RuntimeError("获取 NAS 统计信息失败")
                msg = (
                    f"NAS 地址: //{self.nas_ip_var.get().strip()}/{self.nas_share_var.get().strip()}\n"
                    f"挂载点: {DEFAULT_NAS_MOUNT_POINT}\n\n"
                    f"总大小: {total.strip()}\n"
                    f"文件数: {files.strip()}\n"
                    f"目录数: {dirs.strip()}\n\n"
                    f"{df.strip()}"
                )
                self.app.root.after(0, lambda: messagebox.showinfo("NAS 统计", msg))
                self.app.root.after(0, lambda: self._set_status("统计完成"))
            except Exception as exc:
                self.app.root.after(0, lambda: messagebox.showerror("NAS 云盘", str(exc)))
                self.app.root.after(0, lambda: self._set_status("统计失败"))

        threading.Thread(target=run, daemon=True).start()

    def download_file(self) -> None:
        item_id, item, values = self._selected_item()
        if not item_id or not values:
            messagebox.showwarning("NAS 云盘", "请先选择一个文件")
            return
        if values[2] == "目录":
            self.download_dir()
            return

        file_name = item["text"].replace("📄 ", "", 1)
        save_path = filedialog.asksaveasfilename(
            title="保存文件",
            initialdir=Path.home() / "Downloads",
            initialfile=file_name,
        )
        if not save_path:
            return

        self._set_status(f"下载中: {file_name}")

        def run() -> None:
            cmd = (
                f'scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 '
                f'{self.app.config.user}@{self.app.config.ip}:"{item_id}" "{save_path}"'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)
            if result.returncode != 0:
                self.app.root.after(0, lambda: messagebox.showerror("NAS 云盘", result.stderr or result.stdout or "下载失败"))
                self.app.root.after(0, lambda: self._set_status("下载失败"))
                return
            self.app.root.after(0, lambda: messagebox.showinfo("NAS 云盘", f"文件已保存到:\n{save_path}"))
            self.app.root.after(0, lambda: self._set_status("下载完成"))

        threading.Thread(target=run, daemon=True).start()

    def download_dir(self) -> None:
        item_id, item, values = self._selected_item()
        if not item_id or not values:
            messagebox.showwarning("NAS 云盘", "请先选择一个目录")
            return
        if values[2] == "文件":
            self.download_file()
            return

        save_dir = filedialog.askdirectory(title="选择目录保存位置", initialdir=Path.home() / "Downloads")
        if not save_dir:
            return

        dir_name = item["text"].replace("📁 ", "", 1)
        self._set_status(f"下载目录中: {dir_name}")

        def run() -> None:
            cmd = (
                f'scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 -r '
                f'{self.app.config.user}@{self.app.config.ip}:"{item_id}" "{save_dir}"'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
            if result.returncode != 0:
                self.app.root.after(0, lambda: messagebox.showerror("NAS 云盘", result.stderr or result.stdout or "目录下载失败"))
                self.app.root.after(0, lambda: self._set_status("目录下载失败"))
                return
            self.app.root.after(0, lambda: messagebox.showinfo("NAS 云盘", f"目录已保存到:\n{save_dir}"))
            self.app.root.after(0, lambda: self._set_status("目录下载完成"))

        threading.Thread(target=run, daemon=True).start()
