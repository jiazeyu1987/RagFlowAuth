#!/usr/bin/env python3
"""
RagflowAuth 服务器管理工具

功能：
1. 通过 SSH 执行服务器端工具脚本
2. 快速导航到 Web 管理界面
3. 管理 Docker 容器和镜像
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import webbrowser
import threading
import os
from pathlib import Path

# 配置文件路径
CONFIG_FILE = Path.home() / ".ragflowauth_tool_config.txt"


class ServerConfig:
    """服务器配置"""

    def __init__(self):
        self.ip = "172.30.30.57"
        self.user = "root"
        self.load_config()

    def load_config(self):
        """从文件加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            if key == "SERVER_IP":
                                self.ip = value
                            elif key == "SERVER_USER":
                                self.user = value
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, "w") as f:
                f.write(f"SERVER_IP={self.ip}\n")
                f.write(f"SERVER_USER={self.user}\n")
        except Exception as e:
            print(f"保存配置失败: {e}")


class SSHExecutor:
    """SSH 命令执行器"""

    def __init__(self, ip, user):
        self.ip = ip
        self.user = user

    def execute(self, command, callback=None):
        """执行 SSH 命令"""
        full_command = f"{self.user}@{self.ip} {command}"
        try:
            process = subprocess.Popen(
                ["ssh", full_command],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            output, _ = process.communicate()

            if callback:
                callback(output)

            return process.returncode == 0, output
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            if callback:
                callback(error_msg)
            return False, error_msg


class ToolButton(ttk.Frame):
    """工具按钮组件"""

    def __init__(self, parent, title, description, command, **kwargs):
        super().__init__(parent, **kwargs)
        self.command = command

        # 标题和按钮
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        self.btn = ttk.Button(header_frame, text=title, command=self.on_click, width=30)
        self.btn.pack(side=tk.LEFT)

        # 描述
        desc_label = ttk.Label(self, text=description, wraplength=400, foreground="gray")
        desc_label.pack(fill=tk.X, pady=(0, 5))

        # 输出区域（可选）
        self.output = scrolledtext.ScrolledText(
            self, height=8, width=50, state=tk.DISABLED, font=("Consolas", 9)
        )

    def on_click(self):
        """按钮点击事件"""
        if self.command:
            # 显示输出区域
            self.output.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            self.output.config(state=tk.NORMAL)
            self.output.delete(1.0, tk.END)
            self.output.config(state=tk.DISABLED)

            # 在后台线程执行
            thread = threading.Thread(target=self.command, daemon=True)
            thread.start()

    def append_output(self, text):
        """追加输出"""
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)


class RagflowAuthTool:
    """RagflowAuth 服务器管理工具主窗口"""

    def __init__(self, root):
        self.root = root
        self.root.title("RagflowAuth 服务器管理工具")
        self.root.geometry("900x700")

        self.config = ServerConfig()
        self.ssh_executor = None

        self.setup_ui()

    def setup_ui(self):
        """设置 UI"""
        # 顶部配置区域
        config_frame = ttk.LabelFrame(self.root, text="服务器配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # IP 输入
        ttk.Label(config_frame, text="服务器 IP:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.ip_var = tk.StringVar(value=self.config.ip)
        ip_entry = ttk.Entry(config_frame, textvariable=self.ip_var, width=20)
        ip_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        # 用户名输入
        ttk.Label(config_frame, text="用户名:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.user_var = tk.StringVar(value=self.config.user)
        user_entry = ttk.Entry(config_frame, textvariable=self.user_var, width=15)
        user_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        # 保存按钮
        save_btn = ttk.Button(config_frame, text="保存配置", command=self.save_config)
        save_btn.grid(row=0, column=4)

        # 测试连接按钮
        test_btn = ttk.Button(config_frame, text="测试连接", command=self.test_connection)
        test_btn.grid(row=0, column=5, padx=(5, 0))

        # Notebook（选项卡）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建选项卡
        self.create_tools_tab()
        self.create_web_links_tab()
        self.create_backup_tab()
        self.create_logs_tab()

        # 底部状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 10))

    def create_tools_tab(self):
        """创建工具选项卡"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  工具  ")

        # 滚动容器
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 工具按钮
        tools = [
            {
                "title": "清理 Docker 镜像",
                "desc": "清理服务器上未使用的 Docker 镜像，释放磁盘空间（默认仅保留当前版本）",
                "cmd": "/tmp/cleanup-images.sh --keep 1"
            },
            {
                "title": "清理 Docker 镜像（保留3个版本）",
                "desc": "清理服务器上未使用的 Docker 镜像，保留最近 3 个版本用于回滚",
                "cmd": "/tmp/cleanup-images.sh --keep 3"
            },
            {
                "title": "快速重启容器",
                "desc": "使用现有镜像快速重启容器（不重新构建镜像）",
                "cmd": "/opt/ragflowauth/quick-restart.sh --tag 2025-01-25-scheduler-fix-v2"
            },
            {
                "title": "查看运行中的容器",
                "desc": "列出所有运行中的 Docker 容器及其状态",
                "cmd": "docker ps"
            },
            {
                "title": "查看所有容器",
                "desc": "列出所有 Docker 容器（包括已停止的）",
                "cmd": "docker ps -a"
            },
            {
                "title": "查看 Docker 镜像",
                "desc": "列出所有 Docker 镜像及其大小",
                "cmd": "docker images"
            },
            {
                "title": "查看磁盘使用情况",
                "desc": "显示 Docker 占用的磁盘空间",
                "cmd": "docker system df"
            },
            {
                "title": "查看后端日志",
                "desc": "显示后端容器最近的日志输出",
                "cmd": "docker logs --tail 50 ragflowauth-backend"
            },
            {
                "title": "查看前端日志",
                "desc": "显示前端容器最近的日志输出",
                "cmd": "docker logs --tail 50 ragflowauth-frontend"
            },
            {
                "title": "重启所有容器",
                "desc": "重启 RagflowAuth 的所有容器",
                "cmd": "docker restart ragflowauth-backend ragflowauth-frontend"
            },
            {
                "title": "停止所有容器",
                "desc": "停止 RagflowAuth 的所有容器",
                "cmd": "docker stop ragflowauth-backend ragflowauth-frontend"
            },
            {
                "title": "启动所有容器",
                "desc": "启动 RagflowAuth 的所有容器",
                "cmd": "docker start ragflowauth-backend ragflowauth-frontend"
            },
        ]

        for i, tool in enumerate(tools):
            frame = ttk.LabelFrame(scrollable_frame, text=f"工具 {i+1}", padding=10)
            frame.pack(fill=tk.X, padx=10, pady=5)

            tool_btn = ToolButton(
                frame,
                title=tool["title"],
                description=tool["desc"],
                command=lambda cmd=tool["cmd"]: self.execute_ssh_command(cmd)
            )
            tool_btn.pack(fill=tk.BOTH, expand=True)

    def create_web_links_tab(self):
        """创建 Web 链接选项卡"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Web 管理界面  ")

        # 标题
        title_label = ttk.Label(
            tab,
            text="Web 管理界面快速访问",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=20)

        # 按钮容器
        button_frame = ttk.Frame(tab)
        button_frame.pack(pady=20)

        # 前端按钮（放在第一位）
        frontend_btn = ttk.Button(
            button_frame,
            text="🏠 打开 RagflowAuth 前端",
            command=self.open_frontend,
            width=30
        )
        frontend_btn.grid(row=0, column=0, pady=10, padx=10)

        # 前端说明
        frontend_desc = ttk.Label(
            tab,
            text="RagflowAuth 前端应用\n"
                 "用户登录、知识库管理、文档管理等",
            justify=tk.CENTER,
            foreground="gray"
        )
        frontend_desc.pack(pady=(0, 10))

        # Portainer 按钮
        portainer_btn = ttk.Button(
            button_frame,
            text="🚀 打开 Portainer",
            command=self.open_portainer,
            width=30
        )
        portainer_btn.grid(row=1, column=0, pady=10, padx=10)

        # Portainer 说明
        portainer_desc = ttk.Label(
            tab,
            text="Portainer - Docker 容器管理平台\n"
                 "可以可视化管理容器、镜像、网络等 Docker 资源",
            justify=tk.CENTER,
            foreground="gray"
        )
        portainer_desc.pack(pady=(0, 10))

        # Web 管理界面按钮
        web_btn = ttk.Button(
            button_frame,
            text="🌐 打开 Web 管理界面",
            command=self.open_web_console,
            width=30
        )
        web_btn.grid(row=2, column=0, pady=10, padx=10)

        # Web 管理说明
        web_desc = ttk.Label(
            tab,
            text="Web 管理界面 - RagflowAuth 后台管理\n"
                 "访问 https://172.30.30.57:9090/ 进行后台管理",
            justify=tk.CENTER,
            foreground="gray"
        )
        web_desc.pack(pady=(0, 20))

        # 手动输入 URL
        url_frame = ttk.LabelFrame(tab, text="自定义 URL", padding=10)
        url_frame.pack(fill=tk.X, padx=50, pady=20)

        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, padx=5)
        self.url_var = tk.StringVar(value="http://")
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=40)
        url_entry.grid(row=0, column=1, padx=5, pady=5)

        open_url_btn = ttk.Button(url_frame, text="打开", command=self.open_custom_url)
        open_url_btn.grid(row=0, column=2, padx=5)

    def create_backup_tab(self):
        """创建备份选项卡"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  备份管理  ")

        # 标题
        title_label = ttk.Label(
            tab,
            text="服务器备份管理",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=20)

        # 备份工具
        backup_frame = ttk.LabelFrame(tab, text="备份操作", padding=10)
        backup_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tools = [
            {
                "title": "查看最近的备份",
                "desc": "列出服务器上最近的备份目录",
                "cmd": "ls -lht /opt/ragflowauth/data/backups/ | head -10"
            },
            {
                "title": "查看备份磁盘使用",
                "desc": "显示备份占用的磁盘空间",
                "cmd": "du -sh /opt/ragflowauth/data/backups/* | sort -hr"
            },
            {
                "title": "查看 Windows 共享备份",
                "desc": "查看同步到 Windows 共享的备份",
                "cmd": "ls -lht /mnt/replica/RagflowAuth/ | head -10"
            },
            {
                "title": "检查 SMB 挂载状态",
                "desc": "验证 Windows 共享是否正确挂载",
                "cmd": "df -h | grep replica"
            },
        ]

        for i, tool in enumerate(tools):
            frame = ttk.LabelFrame(backup_frame, text=tool["title"], padding=10)
            frame.pack(fill=tk.X, padx=10, pady=5)

            desc = ttk.Label(frame, text=tool["desc"], foreground="gray", wraplength=600)
            desc.pack(anchor=tk.W, pady=(0, 5))

            btn = ttk.Button(
                frame,
                text="执行",
                command=lambda cmd=tool["cmd"]: self.execute_ssh_command(cmd),
                width=15
            )
            btn.pack(anchor=tk.W)

        # 数据还原区域
        restore_frame = ttk.LabelFrame(tab, text="数据还原", padding=10)
        restore_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 说明
        info_label = ttk.Label(
            restore_frame,
            text="从本地备份文件夹恢复数据到服务器\n"
                 "支持恢复数据库、上传文件和 Docker 镜像",
            foreground="gray",
            justify=tk.CENTER
        )
        info_label.pack(pady=10)

        # 文件夹选择区域
        folder_frame = ttk.Frame(restore_frame)
        folder_frame.pack(fill=tk.X, pady=10)

        ttk.Label(folder_frame, text="备份文件夹:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.restore_folder_var = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.restore_folder_var, width=50)
        folder_entry.grid(row=0, column=1, padx=5, pady=5)

        select_btn = ttk.Button(
            folder_frame,
            text="选择文件夹",
            command=self.select_restore_folder,
            width=12
        )
        select_btn.grid(row=0, column=2, padx=5)

        # 文件夹信息显示
        self.restore_info_label = ttk.Label(restore_frame, text="", foreground="blue", justify=tk.LEFT)
        self.restore_info_label.pack(anchor=tk.W, padx=10, pady=5)

        # 进度显示
        self.restore_progress = ttk.Progressbar(
            restore_frame,
            mode='indeterminate',
            length=400
        )
        self.restore_progress.pack(pady=5)

        self.restore_status_label = ttk.Label(restore_frame, text="", foreground="gray")
        self.restore_status_label.pack(pady=5)

        # 还原按钮
        restore_btn_frame = ttk.Frame(restore_frame)
        restore_btn_frame.pack(pady=10)

        self.restore_btn = ttk.Button(
            restore_btn_frame,
            text="开始还原数据",
            command=self.restore_data,
            state=tk.DISABLED,
            width=20
        )
        self.restore_btn.pack()

        # 输出区域
        output_frame = ttk.LabelFrame(restore_frame, text="还原日志", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.restore_output = scrolledtext.ScrolledText(
            output_frame,
            height=10,
            width=70,
            state=tk.DISABLED,
            font=("Consolas", 9)
        )
        self.restore_output.pack(fill=tk.BOTH, expand=True)

        # 初始化还原状态
        self.restore_images_exists = False
        self.selected_restore_folder = None

    def create_logs_tab(self):
        """创建日志选项卡"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  日志查看  ")

        # 标题
        title_label = ttk.Label(
            tab,
            text="实时日志查看",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=20)

        # 日志查看工具
        log_frame = ttk.LabelFrame(tab, text="日志查看", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tools = [
            {
                "title": "实时后端日志",
                "desc": "实时显示后端容器日志（Ctrl+C 停止）",
                "cmd": "docker logs -f ragflowauth-backend"
            },
            {
                "title": "实时前端日志",
                "desc": "实时显示前端容器日志（Ctrl+C 停止）",
                "cmd": "docker logs -f ragflowauth-frontend"
            },
            {
                "title": "查看系统日志",
                "desc": "显示系统最近的系统日志",
                "cmd": "journalctl -n 50 --no-pager"
            },
            {
                "title": "查看 Docker 服务日志",
                "desc": "显示 Docker 服务的日志",
                "cmd": "journalctl -u docker -n 50 --no-pager"
            },
        ]

        for i, tool in enumerate(tools):
            frame = ttk.LabelFrame(log_frame, text=tool["title"], padding=10)
            frame.pack(fill=tk.X, padx=10, pady=5)

            desc = ttk.Label(frame, text=tool["desc"], foreground="gray", wraplength=600)
            desc.pack(anchor=tk.W, pady=(0, 5))

            btn = ttk.Button(
                frame,
                text="在新窗口中查看",
                command=lambda cmd=tool["cmd"]: self.open_log_window(cmd),
                width=20
            )
            btn.pack(anchor=tk.W)

    def save_config(self):
        """保存配置"""
        self.config.ip = self.ip_var.get()
        self.config.user = self.user_var.get()
        self.config.save_config()
        self.status_bar.config(text="配置已保存")
        messagebox.showinfo("成功", "配置已保存")

    def test_connection(self):
        """测试 SSH 连接"""
        self.update_ssh_executor()
        success, output = self.ssh_executor.execute("echo 'Connection successful'")
        if success and "Connection successful" in output:
            self.status_bar.config(text="连接测试成功")
            messagebox.showinfo("成功", f"成功连接到 {self.config.user}@{self.config.ip}")
        else:
            self.status_bar.config(text="连接测试失败")
            messagebox.showerror("失败", f"无法连接到 {self.config.user}@{self.config.ip}\n\n错误: {output}")

    def update_ssh_executor(self):
        """更新 SSH 执行器"""
        self.config.ip = self.ip_var.get()
        self.config.user = self.user_var.get()
        self.ssh_executor = SSHExecutor(self.config.ip, self.config.user)

    def execute_ssh_command(self, command):
        """执行 SSH 命令"""
        if not self.ssh_executor:
            self.update_ssh_executor()

        self.status_bar.config(text=f"正在执行: {command}")

        def execute():
            def callback(output):
                # 在实际应用中，你可能想要显示输出
                print(output)

            success, output = self.ssh_executor.execute(command, callback)

            if success:
                self.status_bar.config(text="命令执行完成")
                messagebox.showinfo("成功", f"命令执行成功！\n\n输出:\n{output}")
            else:
                self.status_bar.config(text="命令执行失败")
                messagebox.showerror("失败", f"命令执行失败！\n\n错误: {output}")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def open_frontend(self):
        """打开 RagflowAuth 前端"""
        self.update_ssh_executor()
        url = f"http://{self.config.ip}:3001"
        self.status_bar.config(text=f"打开 RagflowAuth 前端: {url}")
        webbrowser.open(url)

    def open_portainer(self):
        """打开 Portainer"""
        self.update_ssh_executor()
        url = f"http://{self.config.ip}:9000"
        self.status_bar.config(text=f"打开 Portainer: {url}")
        webbrowser.open(url)

    def open_web_console(self):
        """打开 Web 管理界面"""
        self.update_ssh_executor()
        url = f"https://{self.config.ip}:9090/"
        self.status_bar.config(text=f"打开 Web 管理界面: {url}")
        webbrowser.open(url)

    def open_custom_url(self):
        """打开自定义 URL"""
        url = self.url_var.get()
        if url and url != "http://":
            self.status_bar.config(text=f"打开: {url}")
            webbrowser.open(url)
        else:
            messagebox.showwarning("警告", "请输入有效的 URL")

    def open_log_window(self, command):
        """在新窗口中查看日志"""
        if not self.ssh_executor:
            self.update_ssh_executor()

        # 创建新窗口
        log_window = tk.Toplevel(self.root)
        log_window.title(f"日志查看: {command}")
        log_window.geometry("800x600")

        # 输出文本框
        output_text = scrolledtext.ScrolledText(
            log_window, wrap=tk.WORD, font=("Consolas", 10)
        )
        output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 关闭按钮
        close_btn = ttk.Button(
            log_window,
            text="关闭",
            command=log_window.destroy
        )
        close_btn.pack(pady=5)

        # 在后台执行命令并实时显示输出
        def tail_log():
            try:
                full_command = f"{self.ssh_executor.user}@{self.ssh_executor.ip} {command}"
                process = subprocess.Popen(
                    ["ssh", full_command],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                for line in process.stdout:
                    output_text.insert(tk.END, line)
                    output_text.see(tk.END)
                    output_text.update()

                process.wait()
            except Exception as e:
                output_text.insert(tk.END, f"\n错误: {str(e)}")

        thread = threading.Thread(target=tail_log, daemon=True)
        thread.start()

    def select_restore_folder(self):
        """选择备份文件夹"""
        folder_path = filedialog.askdirectory(
            title="选择备份文件夹",
            initialdir=r"D:\datas\RagflowAuth"
        )

        if not folder_path:
            return

        self.selected_restore_folder = Path(folder_path)
        self.restore_folder_var.set(str(self.selected_restore_folder))

        # 验证文件夹
        self.validate_restore_folder()

    def validate_restore_folder(self):
        """验证备份文件夹"""
        if not self.selected_restore_folder or not self.selected_restore_folder.exists():
            self.restore_info_label.config(text="❌ 文件夹不存在", foreground="red")
            self.restore_btn.config(state=tk.DISABLED)
            return

        # 检查必要的文件
        auth_db = self.selected_restore_folder / "auth.db"
        uploads_dir = self.selected_restore_folder / "uploads"
        images_tar = self.selected_restore_folder / "images.tar"

        info_text = []
        is_valid = True

        if not auth_db.exists():
            info_text.append("❌ 缺少 auth.db")
            is_valid = False
        else:
            info_text.append(f"✅ 找到数据库: {auth_db.stat().st_size / 1024 / 1024:.2f} MB")

        if uploads_dir.exists() and uploads_dir.is_dir():
            upload_files = list(uploads_dir.rglob("*"))
            info_text.append(f"✅ 找到 uploads 目录: {len(upload_files)} 个文件")
        else:
            info_text.append("⚠️  未找到 uploads 目录")

        # 检查 images.tar
        if images_tar.exists():
            size_mb = images_tar.stat().st_size / 1024 / 1024
            info_text.append(f"✅ 找到 Docker 镜像: {size_mb:.2f} MB")
            self.restore_images_exists = True
        else:
            info_text.append("ℹ️  未找到 Docker 镜像（仅恢复数据）")
            self.restore_images_exists = False

        # 显示信息
        self.restore_info_label.config(text="\n".join(info_text), foreground="blue" if is_valid else "red")

        # 启用/禁用还原按钮
        if is_valid and auth_db.exists():
            self.restore_btn.config(state=tk.NORMAL)
        else:
            self.restore_btn.config(state=tk.DISABLED)

    def append_restore_log(self, text):
        """追加还原日志"""
        self.restore_output.config(state=tk.NORMAL)
        self.restore_output.insert(tk.END, text + "\n")
        self.restore_output.see(tk.END)
        self.restore_output.config(state=tk.DISABLED)
        self.restore_output.update()

    def restore_data(self):
        """执行数据还原"""
        if not self.selected_restore_folder:
            messagebox.showerror("错误", "请先选择备份文件夹")
            return

        # 确认对话框
        restore_type = "数据和 Docker 镜像" if self.restore_images_exists else "数据"
        result = messagebox.askyesno(
            "确认还原",
            f"即将还原 {restore_type} 到服务器\n\n"
            f"源文件夹: {self.selected_restore_folder}\n"
            f"目标服务器: {self.config.ip}\n\n"
            f"⚠️  警告：这将覆盖服务器上的现有数据！\n\n"
            f"是否继续？"
        )

        if not result:
            return

        # 禁用按钮
        self.restore_btn.config(state=tk.DISABLED)
        self.restore_output.config(state=tk.NORMAL)
        self.restore_output.delete(1.0, tk.END)
        self.restore_output.config(state=tk.DISABLED)

        # 启动进度条
        self.restore_progress.start(10)
        self.restore_status_label.config(text="正在准备还原...")

        # 在后台线程执行还原
        thread = threading.Thread(target=self._execute_restore, daemon=True)
        thread.start()

    def _execute_restore(self):
        """执行还原操作（在后台线程中）"""
        try:
            self.append_restore_log("=" * 60)
            self.append_restore_log(f"开始还原: {self.selected_restore_folder}")
            self.append_restore_log("=" * 60)

            # 1. 停止容器
            self.append_restore_log("\n[1/6] 停止 Docker 容器...")
            self.restore_status_label.config(text="正在停止容器...")

            success, output = self.ssh_executor.execute(
                "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true"
            )
            self.append_restore_log(output)

            # 2. 备份服务器现有数据
            self.append_restore_log("\n[2/6] 备份服务器现有数据...")
            self.restore_status_label.config(text="正在备份现有数据...")

            timestamp = subprocess.check_output("powershell -Command 'Get-Date -Format \"yyyyMMdd_HHmmss\"'", shell=True).decode().strip()
            backup_dir = f"/tmp/restore_backup_{timestamp}"

            commands = [
                f"mkdir -p {backup_dir}",
                "cp /opt/ragflowauth/data/auth.db /opt/ragflowauth/data/auth.db.backup 2>/dev/null || true",
                f"cp /opt/ragflowauth/data/auth.db {backup_dir}/ 2>/dev/null || true",
                "rm -rf /opt/ragflowauth/uploads.bak 2>/dev/null || true",
                "cp -r /opt/ragflowauth/uploads /opt/ragflowauth/uploads.bak 2>/dev/null || true",
            ]

            for cmd in commands:
                success, output = self.ssh_executor.execute(cmd)
                self.append_restore_log(f"  {cmd}")
                if not success:
                    self.append_restore_log(f"  ⚠️  警告: {output}")

            self.append_restore_log(f"✅ 现有数据已备份到: {backup_dir}")

            # 3. 上传数据文件
            self.append_restore_log("\n[3/6] 上传数据文件到服务器...")
            self.restore_status_label.config(text="正在上传数据...")

            # 上传 auth.db
            auth_db_local = self.selected_restore_folder / "auth.db"
            if auth_db_local.exists():
                self.append_restore_log(f"  上传 auth.db ({auth_db_local.stat().st_size / 1024 / 1024:.2f} MB)...")
                result = subprocess.run(
                    ["scp", str(auth_db_local), f"{self.config.user}@{self.config.ip}:/opt/ragflowauth/data/auth.db"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.append_restore_log("  ✅ auth.db 上传成功")
                else:
                    raise Exception(f"上传 auth.db 失败: {result.stderr}")

            # 上传 uploads 目录（如果存在）
            uploads_local = self.selected_restore_folder / "uploads"
            if uploads_local.exists() and uploads_local.is_dir():
                self.append_restore_log("  上传 uploads 目录...")
                result = subprocess.run(
                    ["scp", "-r", str(uploads_local) + "/", f"{self.config.user}@{self.config.ip}:/opt/ragflowauth/uploads/"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.append_restore_log("  ✅ uploads 目录上传成功")
                else:
                    self.append_restore_log(f"  ⚠️  uploads 上传失败: {result.stderr}")

            # 4. 上传并加载 Docker 镜像（如果存在）
            if self.restore_images_exists:
                self.append_restore_log("\n[4/6] 上传并加载 Docker 镜像...")
                self.restore_status_label.config(text="正在上传 Docker 镜像...")

                images_tar_local = self.selected_restore_folder / "images.tar"
                size_mb = images_tar_local.stat().st_size / 1024 / 1024
                self.append_restore_log(f"  上传 images.tar ({size_mb:.2f} MB)...")

                # 上传到服务器
                result = subprocess.run(
                    ["scp", str(images_tar_local), f"{self.config.user}@{self.config.ip}:/tmp/images.tar"],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise Exception(f"上传 images.tar 失败: {result.stderr}")

                self.append_restore_log("  ✅ images.tar 上传成功")
                self.append_restore_log("  正在加载 Docker 镜像...")

                # 加载镜像
                success, output = self.ssh_executor.execute("docker load -i /tmp/images.tar")
                if success:
                    self.append_restore_log("  ✅ Docker 镜像加载成功")
                else:
                    raise Exception(f"加载 Docker 镜像失败: {output}")

                # 清理临时文件
                self.ssh_executor.execute("rm -f /tmp/images.tar")
            else:
                self.append_restore_log("\n[4/6] 跳过 Docker 镜像（未找到 images.tar）")

            # 5. 启动容器
            self.append_restore_log("\n[5/6] 启动 Docker 容器...")
            self.restore_status_label.config(text="正在启动容器...")

            success, output = self.ssh_executor.execute(
                "docker start ragflowauth-backend ragflowauth-frontend"
            )
            self.append_restore_log(output)

            if success:
                self.append_restore_log("  ✅ 容器启动成功")
            else:
                self.append_restore_log("  ⚠️  容器启动可能有问题，请检查日志")

            # 6. 验证
            self.append_restore_log("\n[6/6] 验证服务状态...")
            self.restore_status_label.config(text="正在验证服务...")

            import time
            time.sleep(3)  # 等待容器完全启动

            success, output = self.ssh_executor.execute("docker ps | grep ragflowauth")
            self.append_restore_log(output)

            # 完成
            self.append_restore_log("\n" + "=" * 60)
            self.append_restore_log("✅ 数据还原完成！")
            self.append_restore_log("=" * 60)
            self.restore_status_label.config(text="✅ 还原完成")

            # 显示成功消息
            messagebox.showinfo(
                "还原完成",
                f"数据还原成功！\n\n"
                f"可以访问以下地址验证：\n"
                f"• 前端: http://{self.config.ip}:3001\n"
                f"• 后端: http://{self.config.ip}:8001"
            )

        except Exception as e:
            error_msg = f"还原失败: {str(e)}"
            self.append_restore_log(f"\n❌ {error_msg}")
            self.restore_status_label.config(text="❌ 还原失败")
            messagebox.showerror("还原失败", error_msg)

        finally:
            # 恢复按钮状态
            self.restore_progress.stop()
            self.restore_btn.config(state=tk.NORMAL)


def main():
    """主函数"""
    root = tk.Tk()
    app = RagflowAuthTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
