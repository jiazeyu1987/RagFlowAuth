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
import sys
import logging
from pathlib import Path
from datetime import datetime

# ==================== 日志配置 ====================
# 日志文件路径（与 tool.py 同目录）
LOG_FILE = Path(__file__).parent / "tool_log.log"

# 创建 logger
logger = logging.getLogger("RagflowAuthTool")
logger.setLevel(logging.DEBUG)

# 文件处理器（UTF-8 编码，自动换行）
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a')
file_handler.setLevel(logging.DEBUG)

# 控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 日志格式
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 防止重复添加
logger.propagate = False

def log_to_file(message, level="INFO"):
    """写入日志到文件的辅助函数"""
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "DEBUG":
        logger.debug(message)
    else:
        logger.info(message)

# ==================== 配置文件路径 ====================
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
                msg = f"加载配置失败: {e}"
                print(msg)
                log_to_file(msg, "ERROR")

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, "w") as f:
                f.write(f"SERVER_IP={self.ip}\n")
                f.write(f"SERVER_USER={self.user}\n")
        except Exception as e:
            msg = f"保存配置失败: {e}"
            print(msg)
            log_to_file(msg, "ERROR")


class SSHExecutor:
    """SSH 命令执行器"""

    def __init__(self, ip, user):
        self.ip = ip
        self.user = user

    def execute(self, command, callback=None, timeout_seconds=310):
        """执行 SSH 命令

        Args:
            command: 要执行的命令
            callback: 可选的回调函数
            timeout_seconds: 超时时间（秒），默认 310 秒（5分钟）
        """
        # 使用双引号包裹命令，转义内部的双引号和特殊字符
        escaped_command = command.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
        # 添加 BatchMode=yes 避免等待密码输入
        full_command = f'ssh -o BatchMode=yes -o ConnectTimeout=10 {self.user}@{self.ip} "{escaped_command}"'

        # 调试日志（仅当命令较长时显示）
        if len(command) > 100:
            debug_cmd = command[:97] + "..."
        else:
            debug_cmd = command

        # 记录 SSH 命令到日志文件
        log_to_file(f"[SSH] 执行命令: {debug_cmd}", "DEBUG")

        try:
            # 执行命令
            process = subprocess.Popen(
                full_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            # 添加超时
            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                timeout_minutes = timeout_seconds / 60
                error_msg = f"SSH 命令超时（超过{timeout_minutes:.1f}分钟）: {command[:100]}..."
                log_to_file(f"[SSH] {error_msg}", "ERROR")
                raise Exception(error_msg)

            # 合并 stdout 和 stderr
            output = stdout + stderr

            # 记录命令执行结果
            if process.returncode == 0:
                log_to_file(f"[SSH] 命令执行成功", "DEBUG")
            else:
                log_to_file(f"[SSH] 命令执行失败 (返回码: {process.returncode})", "ERROR")
                if output.strip():
                    log_to_file(f"[SSH] 错误输出: {output}", "ERROR")

            if callback:
                callback(output)

            return process.returncode == 0, output
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            log_to_file(f"[SSH] {error_msg}", "ERROR")
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
        # 同时记录到日志文件
        log_to_file(f"[TOOL] {text.strip()}", "INFO")


class RagflowAuthTool:
    """RagflowAuth 服务器管理工具主窗口"""

    def __init__(self, root):
        self.root = root
        self.root.title("RagflowAuth 服务器管理工具")
        self.root.geometry("900x700")

        self.config = ServerConfig()
        self.ssh_executor = None

        # 记录初始化
        log_to_file(f"UI 初始化完成，默认服务器: {self.config.user}@{self.config.ip}")

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
        self.create_restore_tab()
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
                "title": "快速部署",
                "desc": "快速部署到服务器（使用 Windows 本地构建的镜像）",
                "cmd": "quick-deploy"
            },
            {
                "title": "快速重启容器",
                "desc": "使用现有镜像快速重启容器（不重新构建镜像）",
                "cmd": "/opt/ragflowauth/quick-restart.sh --tag 2025-01-25-scheduler-fix-v2"
            },
            {
                "title": "查看运行中的容器",
                "desc": "列出所有运行中的 Docker 容器及其状态（包括挂载信息）",
                "cmd": "__show_containers_with_mounts__"
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

    def create_restore_tab(self):
        """创建数据还原选项卡"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  数据还原  ")

        # 标题
        title_label = ttk.Label(
            tab,
            text="数据还原",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=20)

        # 说明
        info_label = ttk.Label(
            tab,
            text="从本地备份文件夹恢复数据到服务器\n"
                 "支持恢复：RagflowAuth 数据、上传文件、Docker 镜像、RAGFlow 数据 (volumes)",
            foreground="gray",
            justify=tk.CENTER
        )
        info_label.pack(pady=10)

        # 文件夹选择区域
        folder_frame = ttk.LabelFrame(tab, text="选择备份文件夹", padding=10)
        folder_frame.pack(fill=tk.X, padx=20, pady=10)

        input_frame = ttk.Frame(folder_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="备份文件夹:").pack(side=tk.LEFT, padx=5)
        self.restore_folder_var = tk.StringVar()
        folder_entry = ttk.Entry(input_frame, textvariable=self.restore_folder_var, width=50)
        folder_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        select_btn = ttk.Button(
            input_frame,
            text="浏览",
            command=self.select_restore_folder,
            width=10
        )
        select_btn.pack(side=tk.LEFT, padx=5)

        # 文件夹信息显示
        self.restore_info_label = ttk.Label(folder_frame, text="", foreground="blue", justify=tk.LEFT)
        self.restore_info_label.pack(anchor=tk.W, padx=10, pady=5)

        # 还原选项
        options_frame = ttk.LabelFrame(tab, text="还原选项", padding=10)
        options_frame.pack(fill=tk.X, padx=20, pady=10)

        self.restore_options = {
            "auth_db": tk.BooleanVar(value=True),
            "uploads": tk.BooleanVar(value=True),
            "images": tk.BooleanVar(value=False),
            "volumes": tk.BooleanVar(value=True),
        }

        ttk.Checkbutton(
            options_frame,
            text="RagflowAuth 数据库",
            variable=self.restore_options["auth_db"]
        ).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Checkbutton(
            options_frame,
            text="上传文件 (uploads)",
            variable=self.restore_options["uploads"]
        ).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Checkbutton(
            options_frame,
            text="Docker 镜像",
            variable=self.restore_options["images"]
        ).pack(anchor=tk.W, padx=10, pady=2)

        ttk.Checkbutton(
            options_frame,
            text="RAGFlow 数据 (volumes)",
            variable=self.restore_options["volumes"]
        ).pack(anchor=tk.W, padx=10, pady=2)

        # 进度显示
        progress_frame = ttk.LabelFrame(tab, text="还原进度", padding=10)
        progress_frame.pack(fill=tk.X, padx=20, pady=10)

        self.restore_progress = ttk.Progressbar(
            progress_frame,
            mode='indeterminate',
            length=400
        )
        self.restore_progress.pack(pady=5)

        self.restore_status_label = ttk.Label(progress_frame, text="", foreground="gray")
        self.restore_status_label.pack(pady=5)

        # 还原按钮
        restore_btn_frame = ttk.Frame(tab)
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
        output_frame = ttk.LabelFrame(tab, text="还原日志", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        self.restore_output = scrolledtext.ScrolledText(
            output_frame,
            height=15,
            width=80,
            state=tk.DISABLED,
            font=("Consolas", 9)
        )
        self.restore_output.pack(fill=tk.BOTH, expand=True)

        # 初始化还原状态
        self.restore_images_exists = False
        self.restore_volumes_exists = False
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
        msg = "[INFO] 配置已保存"
        print(msg)
        log_to_file(msg)
        messagebox.showinfo("成功", "配置已保存")

    def test_connection(self):
        """测试 SSH 连接"""
        self.update_ssh_executor()
        success, output = self.ssh_executor.execute("echo 'Connection successful'")
        if success and "Connection successful" in output:
            self.status_bar.config(text="连接测试成功")
            msg = f"[INFO] 成功连接到 {self.config.user}@{self.config.ip}"
            print(msg)
            log_to_file(msg)
            messagebox.showinfo("成功", f"成功连接到 {self.config.user}@{self.config.ip}")
        else:
            self.status_bar.config(text="连接测试失败")
            msg = f"[ERROR] 无法连接到 {self.config.user}@{self.config.ip}\n错误: {output}"
            print(msg)
            log_to_file(msg, "ERROR")
            messagebox.showerror("失败", f"无法连接到 {self.config.user}@{self.config.ip}\n\n错误: {output}")

    def update_ssh_executor(self):
        """更新 SSH 执行器"""
        self.config.ip = self.ip_var.get()
        self.config.user = self.user_var.get()
        self.ssh_executor = SSHExecutor(self.config.ip, self.config.user)

    def execute_ssh_command(self, command):
        """执行 SSH 命令"""
        # 特殊处理：快速部署
        if command == "quick-deploy":
            self.run_quick_deploy()
            return

        # 特殊处理：显示容器列表和挂载状态
        if command == "__show_containers_with_mounts__":
            self.show_containers_with_mounts()
            return

        if not self.ssh_executor:
            self.update_ssh_executor()

        self.status_bar.config(text=f"正在执行: {command}")

        def execute():
            def callback(output):
                # 在实际应用中，你可能想要显示输出
                print(output)
                log_to_file(f"[SSH-CMD] {output.strip()}")

            success, output = self.ssh_executor.execute(command, callback)

            if success:
                self.status_bar.config(text="命令执行完成")
                msg = f"[INFO] 命令执行成功！\n输出:\n{output}"
                print(msg)
                log_to_file(msg)
                messagebox.showinfo("成功", f"命令执行成功！\n\n输出:\n{output}")
            else:
                self.status_bar.config(text="命令执行失败")
                msg = f"[ERROR] 命令执行失败！\n错误: {output}"
                print(msg)
                log_to_file(msg, "ERROR")
                messagebox.showerror("失败", f"命令执行失败！\n\n错误: {output}")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def run_quick_deploy(self):
        """执行快速部署"""
        self.status_bar.config(text="正在执行快速部署...")

        def execute():
            try:
                # 调用 quick-deploy.ps1
                script_path = Path(__file__).parent / "tool" / "scripts" / "quick-deploy.ps1"
                if not script_path.exists():
                    raise FileNotFoundError(f"部署脚本不存在: {script_path}")

                # 执行 PowerShell 脚本
                result = subprocess.run(
                    ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )

                if result.returncode == 0:
                    self.status_bar.config(text="快速部署完成")
                    msg = f"[INFO] 快速部署成功！\n输出:\n{result.stdout}"
                    print(msg)
                    log_to_file(msg)
                    messagebox.showinfo("部署成功", f"快速部署成功！\n\n{result.stdout}")
                else:
                    self.status_bar.config(text="快速部署失败")
                    msg = f"[ERROR] 快速部署失败！\n错误:\n{result.stderr}"
                    print(msg)
                    log_to_file(msg, "ERROR")
                    messagebox.showerror("部署失败", f"快速部署失败！\n\n{result.stderr}")
            except Exception as e:
                self.status_bar.config(text="快速部署失败")
                msg = f"[ERROR] 快速部署异常: {str(e)}"
                print(msg)
                log_to_file(msg, "ERROR")
                messagebox.showerror("部署失败", f"快速部署异常！\n\n{str(e)}")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def show_containers_with_mounts(self):
        """显示容器列表和挂载状态"""
        self.status_bar.config(text="正在获取容器信息...")
        log_to_file("[CONTAINER-CHECK] 开始检查容器挂载状态")

        def execute():
            try:
                print("[DEBUG] 步骤 1: 初始化SSH连接...")
                log_to_file("[CONTAINER-CHECK] 步骤 1: 初始化SSH连接")
                if not self.ssh_executor:
                    self.update_ssh_executor()

                # 获取运行中的容器列表
                print("[DEBUG] 步骤 2: 获取容器列表...")
                log_to_file("[CONTAINER-CHECK] 步骤 2: 获取容器列表")
                success, output = self.ssh_executor.execute("docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'")
                print(f"[DEBUG] 获取容器列表: success={success}, output_length={len(output) if output else 0}")
                log_to_file(f"[CONTAINER-CHECK] 获取容器列表结果: success={success}")

                if not success:
                    error_msg = f"获取容器列表失败：\n{output}"
                    print(f"[ERROR] {error_msg}")
                    log_to_file(f"[CONTAINER-CHECK] ERROR: {error_msg}", "ERROR")
                    messagebox.showerror("错误", error_msg)
                    self.status_bar.config(text="获取容器列表失败")
                    return

                containers = []
                for line in output.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_name = parts[0]
                            containers.append(container_name)

                print(f"[DEBUG] 找到 {len(containers)} 个运行中的容器")
                log_to_file(f"[CONTAINER-CHECK] 找到 {len(containers)} 个运行中的容器")

                # 检查每个容器的挂载状态
                result_text = "=== 运行中的容器及挂载状态 ===\n\n"
                result_text += f"{'容器名称':<30} {'挂载检查':<50} {'状态':<15}\n"
                result_text += "=" * 95 + "\n"

                # 首先获取数据库配置
                print("[DEBUG] 步骤 3: 获取数据库配置...")
                log_to_file("[CONTAINER-CHECK] 步骤 3: 获取数据库配置")
                config_cmd = "docker exec ragflowauth-backend python -c \"import sqlite3; conn = sqlite3.connect('/app/data/auth.db'); cursor = conn.cursor(); cursor.execute('SELECT replica_target_path FROM data_security_settings LIMIT 1'); row = cursor.fetchone(); print(row[0] if row else 'NOT_SET'); conn.close()\""
                success, config_output = self.ssh_executor.execute(config_cmd)
                print(f"[DEBUG] 获取配置: success={success}, output={config_output}")
                log_to_file(f"[CONTAINER-CHECK] 配置查询结果: {config_output}")

                if config_output:
                    config_output = '\n'.join(line for line in config_output.split('\n')
                                              if 'close - IO is still pending' not in line
                                              and 'read:' not in line
                                              and 'write:' not in line
                                              and 'io:' not in line).strip()

                # 定义颜色代码
                GREEN = "\033[92m"
                RED = "\033[91m"
                RESET = "\033[0m"

                # 检查配置是否符合预期
                config_ok = config_output == "/mnt/replica/RagflowAuth"
                config_status = f"{GREEN}✓ 符合预期{RESET}" if config_ok else f"{RED}✗ 配置错误{RESET}"
                result_text += f"配置的复制路径: {config_output} [{config_status}]\n"
                result_text += "-" * 95 + "\n"

                # 检查每个容器
                print(f"[DEBUG] 步骤 4: 检查 {len(containers)} 个容器的挂载点...")
                log_to_file(f"[CONTAINER-CHECK] 步骤 4: 检查容器挂载点")

                for idx, container in enumerate(containers):
                    print(f"[DEBUG] 检查容器 {idx+1}/{len(containers)}: {container}")
                    log_to_file(f"[CONTAINER-CHECK] 检查容器: {container}")

                    try:
                        # 获取容器状态
                        status_cmd = "docker inspect {} --format '{{{{.State.Status}}}}' 2>/dev/null".format(container)
                        success, status = self.ssh_executor.execute(status_cmd)
                        if status:
                            status = '\n'.join(line for line in status.split('\n')
                                             if 'close - IO is still pending' not in line
                                             and 'read:' not in line
                                             and 'write:' not in line
                                             and 'io:' not in line).strip()

                        if not success or not status:
                            status = "未知"
                            status_colored = f"{RED}{status}{RESET}"
                        else:
                            # 状态用颜色标记
                            if status == "running":
                                status_colored = f"{GREEN}{status}{RESET}"
                            else:
                                status_colored = f"{RED}{status}{RESET}"

                        # 只检查 ragflowauth-backend 的挂载
                        if container == "ragflowauth-backend":
                            # 获取容器的所有挂载点（JSON格式）
                            inspect_cmd = "docker inspect {} --format '{{{{json .Mounts}}}}' 2>/dev/null".format(container)
                            success, mounts_json = self.ssh_executor.execute(inspect_cmd)

                            if not success:
                                mount_info = f"{RED}⚠️  无法获取挂载信息{RESET}"
                            else:
                                # 清理输出中的SSH警告信息
                                if mounts_json:
                                    mounts_json = '\n'.join(line for line in mounts_json.split('\n')
                                                               if 'close - IO is still pending' not in line
                                                               and 'read:' not in line
                                                               and 'write:' not in line
                                                               and 'io:' not in line).strip()

                                # 检查是否有 /mnt/replica 挂载
                                has_replica_mount = False
                                mount_info = ""

                                if mounts_json and "YES" not in mounts_json:
                                    import json
                                    try:
                                        mounts = json.loads(mounts_json)
                                        replica_mounts = [m for m in mounts if '/mnt/replica' in m.get('Destination', '')]
                                        if replica_mounts:
                                            has_replica_mount = True
                                            for m in replica_mounts:
                                                source = m.get('Source', '')
                                                dest = m.get('Destination', '')
                                                if dest == '/mnt/replica':
                                                    mount_info = f"{GREEN}✓ {source} -> {dest}{RESET}"
                                                else:
                                                    mount_info = f"{RED}⚠️  {source} -> {dest}{RESET}"
                                    except json.JSONDecodeError as e:
                                        print(f"[DEBUG]   JSON解析失败: {e}")
                                        mount_info = f"{RED}⚠️  挂载信息解析失败{RESET}"

                                if not has_replica_mount and not mount_info:
                                    mount_info = f"{RED}✗ 未挂载 /mnt/replica{RESET}"

                                print(f"[DEBUG]   挂载状态: {mount_info}")

                            result_text += f"{container:<30} {mount_info:<50} {status_colored:<15}\n"
                        else:
                            # 其他容器不显示挂载信息
                            result_text += f"{container:<30} {'(无需挂载)':<50} {status_colored:<15}\n"

                    except Exception as e:
                        error_msg = f"检查容器 {container} 时出错: {str(e)}"
                        print(f"[ERROR] {error_msg}")
                        log_to_file(f"[CONTAINER-CHECK] ERROR: {error_msg}", "ERROR")
                        result_text += f"{container:<30} {RED}⚠️  检查失败{RESET:<50} {status_colored:<15}\n"

                print("[DEBUG] 步骤 5: 生成结果...")
                log_to_file("[CONTAINER-CHECK] 步骤 5: 生成结果")

                result_text += "\n" + "=" * 95 + "\n"
                result_text += f"说明: {GREEN}✓ = 符合预期{RESET}, {RED}✗ = 需要修复{RESET}\n"

                # 显示结果
                print("[DEBUG] 显示结果窗口...")
                log_to_file(f"[CONTAINER-CHECK] 显示结果窗口")
                print(result_text)
                self.show_result_window("容器列表及挂载状态", result_text)
                self.status_bar.config(text="容器信息获取完成")
                log_to_file("[CONTAINER-CHECK] 完成")

            except Exception as e:
                error_msg = f"获取容器信息失败：{str(e)}"
                print(f"[ERROR] {error_msg}")
                log_to_file(f"[CONTAINER-CHECK] ERROR: {error_msg}", "ERROR")
                import traceback
                traceback.print_exc()
                messagebox.showerror("错误", error_msg)
                self.status_bar.config(text="获取容器信息失败")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def show_result_window(self, title, content):
        """显示结果窗口（支持ANSI颜色代码）"""
        result_window = tk.Toplevel(self.root)
        result_window.title(title)
        result_window.geometry("800x600")

        # 添加文本框
        text_frame = ttk.Frame(result_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_widget, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 定义颜色tag
        text_widget.tag_config("green", foreground="green")
        text_widget.tag_config("red", foreground="red")

        # 解析ANSI颜色代码并插入文本
        import re
        ansi_escape = re.compile(r'\033\[(\d+(;\d+)*)?m')

        lines = content.split('\n')
        for line in lines:
            last_pos = 0
            current_tag = None

            for match in ansi_escape.finditer(line):
                # 插入普通文本
                if match.start() > last_pos:
                    normal_text = line[last_pos:match.start()]
                    if current_tag:
                        text_widget.insert(tk.END, normal_text, current_tag)
                    else:
                        text_widget.insert(tk.END, normal_text)

                # 解析颜色代码
                code = match.group()
                if '\033[92m' in code:  # 绿色
                    current_tag = "green"
                elif '\033[91m' in code:  # 红色
                    current_tag = "red"
                elif '\033[0m' in code:  # 重置
                    current_tag = None

                last_pos = match.end()

            # 插入剩余文本
            if last_pos < len(line):
                remaining_text = line[last_pos:]
                if current_tag:
                    text_widget.insert(tk.END, remaining_text, current_tag)
                else:
                    text_widget.insert(tk.END, remaining_text)

            text_widget.insert(tk.END, '\n')

        text_widget.config(state=tk.DISABLED)

        # 添加关闭按钮
        close_button = ttk.Button(result_window, text="关闭", command=result_window.destroy)
        close_button.pack(pady=10)

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
            log_to_file(f"[URL] 打开自定义 URL: {url}")
            webbrowser.open(url)
        else:
            msg = "[WARNING] 请输入有效的 URL"
            print(msg)
            log_to_file(msg, "WARNING")
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

        # 记录到日志
        log_to_file(f"[RESTORE] 选择备份文件夹: {self.selected_restore_folder}")

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
        volumes_dir = self.selected_restore_folder / "volumes"

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

        # 检查 volumes 目录（RAGFlow 数据）
        if volumes_dir.exists() and volumes_dir.is_dir():
            volume_items = list(volumes_dir.rglob("*"))
            info_text.append(f"✅ 找到 RAGFlow 数据 (volumes): {len(volume_items)} 个文件")
            self.restore_volumes_exists = True
        else:
            info_text.append("ℹ️  未找到 RAGFlow 数据 (volumes)")
            self.restore_volumes_exists = False

        # 显示信息
        self.restore_info_label.config(text="\n".join(info_text), foreground="blue" if is_valid else "red")

        # 记录验证结果到日志
        log_to_file(f"[RESTORE] 备份验证结果:\n" + "\n".join(info_text))

        # 启用/禁用还原按钮
        if is_valid and auth_db.exists():
            self.restore_btn.config(state=tk.NORMAL)
        else:
            self.restore_btn.config(state=tk.DISABLED)

    def append_restore_log(self, text):
        """追加还原日志（线程安全）"""
        # 记录到日志文件
        log_to_file(f"[RESTORE] {text}", "INFO")

        # 使用 after 方法将 GUI 更新调度到主线程
        def _update():
            self.restore_output.config(state=tk.NORMAL)
            self.restore_output.insert(tk.END, text + "\n")
            self.restore_output.see(tk.END)
            self.restore_output.config(state=tk.DISABLED)
            self.restore_output.update_idletasks()

        # 如果已经在主线程中，直接执行；否则使用 after 调度
        if threading.current_thread() is threading.main_thread():
            _update()
        else:
            # 从后台线程更新 GUI，需要使用 after
            self.root.after(0, _update)

    def update_restore_status(self, text):
        """更新还原状态标签（线程安全）"""
        # 记录到日志文件
        log_to_file(f"[RESTORE-STATUS] {text}", "INFO")

        def _update():
            self.restore_status_label.config(text=text)

        if threading.current_thread() is threading.main_thread():
            _update()
        else:
            self.root.after(0, _update)

    def stop_restore_progress(self):
        """停止还原进度条并恢复按钮（线程安全）"""
        def _update():
            self.restore_progress.stop()
            self.restore_btn.config(state=tk.NORMAL)

        if threading.current_thread() is threading.main_thread():
            _update()
        else:
            self.root.after(0, _update)

    def restore_data(self):
        """执行数据还原"""
        if not self.selected_restore_folder:
            msg = "[ERROR] 请先选择备份文件夹"
            print(msg)
            log_to_file(msg, "ERROR")
            messagebox.showerror("错误", "请先选择备份文件夹")
            return

        # 确保 SSH 执行器已初始化
        self.update_ssh_executor()

        # 确认对话框
        restore_items = []
        restore_items.append("RagflowAuth 数据")
        if self.restore_images_exists:
            restore_items.append("Docker 镜像")
        if self.restore_volumes_exists:
            restore_items.append("RAGFlow 数据 (volumes)")

        restore_type = " 和 ".join(restore_items)
        result = messagebox.askyesno(
            "确认还原",
            f"即将还原 {restore_type} 到服务器\n\n"
            f"源文件夹: {self.selected_restore_folder}\n"
            f"目标服务器: {self.config.ip}\n\n"
            f"⚠️  警告：这将覆盖服务器上的现有数据！\n\n"
            f"是否继续？"
        )

        if not result:
            log_to_file(f"[RESTORE] 用户取消还原操作")
            return

        # 记录还原开始
        log_to_file(f"[RESTORE] 用户确认还原操作")
        log_to_file(f"[RESTORE] 源文件夹: {self.selected_restore_folder}")
        log_to_file(f"[RESTORE] 目标服务器: {self.config.user}@{self.config.ip}")
        log_to_file(f"[RESTORE] 还原内容: {restore_type}")

        # 禁用按钮
        self.restore_btn.config(state=tk.DISABLED)
        self.restore_output.config(state=tk.NORMAL)
        self.restore_output.delete(1.0, tk.END)
        self.restore_output.config(state=tk.DISABLED)

        # 启动进度条
        self.restore_progress.start(10)
        self.update_restore_status("正在准备还原...")

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
            self.append_restore_log("\n[1/7] 停止 Docker 容器...")
            self.update_restore_status("正在停止容器...")

            # 停止 RagflowAuth 容器
            self.append_restore_log("  停止 RagflowAuth 容器...")
            success, output = self.ssh_executor.execute(
                "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true"
            )
            self.append_restore_log(f"  {output}")

            # 停止 RAGFlow 容器（如果存在 volumes）
            if self.restore_volumes_exists:
                self.append_restore_log("  停止 RAGFlow 容器...")
                success, output = self.ssh_executor.execute(
                    "cd /opt/ragflowauth/ragflow_compose && docker compose down 2>/dev/null || true"
                )
                self.append_restore_log(f"  {output}")
            else:
                self.append_restore_log("  跳过 RAGFlow 容器（未找到 volumes 数据）")

            # 2. 备份服务器现有数据
            self.append_restore_log("\n[2/7] 备份服务器现有数据...")
            self.update_restore_status("正在备份现有数据...")

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

            self.append_restore_log(f"✅ RagflowAuth 数据已备份到: {backup_dir}")

            # 3. 上传数据文件
            self.append_restore_log("\n[3/7] 上传 RagflowAuth 数据文件...")
            self.update_restore_status("正在上传 RagflowAuth 数据...")

            # 上传 auth.db
            auth_db_local = self.selected_restore_folder / "auth.db"
            if auth_db_local.exists():
                self.append_restore_log(f"  上传 auth.db ({auth_db_local.stat().st_size / 1024 / 1024:.2f} MB)...")
                result = subprocess.run(
                    ["scp", "-o", "BatchMode=yes", str(auth_db_local), f"{self.config.user}@{self.config.ip}:/opt/ragflowauth/data/auth.db"],
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
                    ["scp", "-o", "BatchMode=yes", "-r", str(uploads_local) + "/", f"{self.config.user}@{self.config.ip}:/opt/ragflowauth/uploads/"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.append_restore_log("  ✅ uploads 目录上传成功")
                else:
                    self.append_restore_log(f"  ⚠️  uploads 上传失败: {result.stderr}")

            # 4. 上传并加载 Docker 镜像（如果存在）
            if self.restore_images_exists:
                self.append_restore_log("\n[4/7] 上传并加载 Docker 镜像...")
                self.update_restore_status("正在上传 Docker 镜像...")

                # 确保 Docker 磁盘挂载点存在
                self.ssh_executor.execute("mkdir -p /var/lib/docker/tmp")

                images_tar_local = self.selected_restore_folder / "images.tar"
                size_mb = images_tar_local.stat().st_size / 1024 / 1024
                self.append_restore_log(f"  上传 images.tar ({size_mb:.2f} MB) 到 /var/lib/docker/tmp...")

                # 上传到 Docker 磁盘挂载点
                import time
                start_time = time.time()

                result = subprocess.run(
                    ["scp", "-o", "BatchMode=yes", str(images_tar_local), f"{self.config.user}@{self.config.ip}:/var/lib/docker/tmp/images.tar"],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    log_to_file(f"[RESTORE] 上传 images.tar 失败: {result.stderr}", "ERROR")
                    raise Exception(f"上传 images.tar 失败: {result.stderr}")

                elapsed = time.time() - start_time
                self.append_restore_log("  ✅ images.tar 上传成功")
                log_to_file(f"[RESTORE] images.tar 上传完成: {size_mb:.2f} MB 用时 {elapsed:.1f} 秒 ({size_mb/elapsed:.2f} MB/s)")
                self.append_restore_log("  正在加载 Docker 镜像...")

                # 加载镜像
                success, output = self.ssh_executor.execute("docker load -i /var/lib/docker/tmp/images.tar")
                if success:
                    self.append_restore_log("  ✅ Docker 镜像加载成功")
                else:
                    raise Exception(f"加载 Docker 镜像失败: {output}")

                # 清理临时文件
                self.ssh_executor.execute("rm -f /var/lib/docker/tmp/images.tar")
            else:
                self.append_restore_log("\n[4/7] 跳过 Docker 镜像（未找到 images.tar）")

            # 4.5. 上传 RAGFlow volumes（如果存在）
            if self.restore_volumes_exists:
                self.append_restore_log("\n[5/7] 上传 RAGFlow 数据 (volumes)...")
                self.update_restore_status("正在上传 RAGFlow 数据...")

                volumes_local = self.selected_restore_folder / "volumes"
                self.append_restore_log(f"  本地 volumes 目录: {volumes_local}")

                # 先确保服务器上的目录存在
                self.append_restore_log("  [步骤 1/6] 准备服务器目录...")
                self.append_restore_log("    执行: mkdir -p /opt/ragflowauth/ragflow_compose")
                success, output = self.ssh_executor.execute("mkdir -p /opt/ragflowauth/ragflow_compose")
                if success:
                    self.append_restore_log("    ✅ 目录创建成功")
                else:
                    self.append_restore_log(f"    ⚠️  目录创建输出: {output}")

                # 先备份服务器上的 RAGFlow volumes（如果存在）
                self.append_restore_log("  [步骤 2/6] 备份服务器上的 RAGFlow volumes...")
                backup_cmd = (
                    "cd /opt/ragflowauth/ragflow_compose && "
                    "tar -czf /var/lib/docker/tmp/ragflow_volumes_backup_$(date +%Y%m%d_%H%M%S).tar.gz volumes 2>/dev/null || true"
                )
                self.append_restore_log(f"    执行: {backup_cmd}")
                success, output = self.ssh_executor.execute(backup_cmd)
                if success:
                    self.append_restore_log("    ✅ 备份成功")
                else:
                    self.append_restore_log(f"    ⚠️  备份输出: {output}")

                # 删除服务器上的旧 volumes 目录（如果存在）
                self.append_restore_log("  [步骤 3/6] 清理服务器上的旧 volumes目录...")
                self.append_restore_log("    执行: rm -rf /opt/ragflowauth/ragflow_compose/volumes")
                success, output = self.ssh_executor.execute("rm -rf /opt/ragflowauth/ragflow_compose/volumes")
                if success:
                    self.append_restore_log("    ✅ 清理成功")
                else:
                    self.append_restore_log(f"    ⚠️  清理输出: {output}")

                # 在本地打包 volumes 目录
                self.append_restore_log("  [步骤 4/6] 打包本地 volumes 目录...")
                import tarfile
                import tempfile

                self.append_restore_log(f"    创建临时文件...")
                temp_tar = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False)
                temp_tar_path = temp_tar.name
                temp_tar.close()
                self.append_restore_log(f"    临时文件: {temp_tar_path}")

                try:
                    self.append_restore_log(f"    开始压缩: {volumes_local} -> {temp_tar_path}")
                    with tarfile.open(temp_tar_path, "w:gz") as tar:
                        tar.add(volumes_local, arcname="volumes")

                    size_mb = os.path.getsize(temp_tar_path) / 1024 / 1024
                    self.append_restore_log(f"    ✅ 压缩完成，大小: {size_mb:.2f} MB")

                    # 上传压缩包到服务器
                    self.append_restore_log("  [步骤 5/6] 上传压缩包到服务器...")
                    self.append_restore_log(f"    目标: {self.config.user}@{self.config.ip}:/var/lib/docker/tmp/volumes.tar.gz")
                    self.append_restore_log(f"    预计需要时间: {size_mb:.2f} MB / 网络速度 ≈ 10秒 ~ 1分钟")

                    import time
                    import sys
                    start_time = time.time()

                    # 方案: 使用 pscp (PuTTY) 或 scp with SSH key
                    # 先检查是否在 Windows 上
                    is_windows = sys.platform == 'win32'
                    self.append_restore_log(f"    平台检测: {'Windows' if is_windows else 'Linux/Mac'}")

                    try:
                        if is_windows:
                            # Windows: 使用 PowerShell + WinSCP-Portable 或直接 scp
                            self.append_restore_log("    检测到 Windows，使用 SCP...")

                            # 检查 scp 是否可用
                            self.append_restore_log("    检查 scp 命令...")
                            scp_check = subprocess.run(["where", "scp"], capture_output=True, text=True, shell=True)
                            self.append_restore_log(f"    where scp 返回码: {scp_check.returncode}")

                            if scp_check.returncode != 0:
                                error_msg = (
                                    "Windows 上找不到 scp 命令。\n\n"
                                    "解决方案：\n"
                                    "1. 安装 Git for Windows（包括 Git Bash）\n"
                                    "2. 或安装 WSL (Windows Subsystem for Linux)\n"
                                    "3. 或使用 WinSCP 图形界面手动上传文件"
                                )
                                self.append_restore_log(f"    ❌ {error_msg}")
                                raise Exception(error_msg)

                            scp_path = scp_check.stdout.strip()
                            self.append_restore_log(f"    ✅ 找到 scp: {scp_path}")

                            # 方案1: 尝试使用 scp（如果有 Git Bash 或 WSL）
                            self.append_restore_log(f"    准备执行 SCP 命令...")
                            self.append_restore_log(f"    源文件: {temp_tar_path}")
                            self.append_restore_log(f"    目标: {self.config.user}@{self.config.ip}:/var/lib/docker/tmp/volumes.tar.gz")

                            cmd = ["scp", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
                                   temp_tar_path, f"{self.config.user}@{self.config.ip}:/var/lib/docker/tmp/volumes.tar.gz"]
                            self.append_restore_log(f"    命令: {' '.join(cmd)}")

                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True
                            )

                            elapsed = time.time() - start_time
                            self.append_restore_log(f"    SCP 执行完成，耗时: {elapsed:.1f}秒")
                            self.append_restore_log(f"    SCP 退出码: {result.returncode}")

                            if result.returncode == 0:
                                self.append_restore_log(f"    ✅ 上传成功 (耗时: {elapsed:.1f}秒)")
                                log_to_file(f"[RESTORE] volumes.tar.gz 上传完成: {size_mb:.2f} MB 用时 {elapsed:.1f} 秒 ({size_mb/elapsed:.2f} MB/s)")
                            else:
                                # SCP 失败，显示详细错误
                                stdout = result.stdout.strip() if result.stdout else "(空)"
                                stderr = result.stderr.strip() if result.stderr else "(空)"
                                self.append_restore_log(f"    ❌ SCP 失败")
                                self.append_restore_log(f"    stdout: {stdout}")
                                self.append_restore_log(f"    stderr: {stderr}")

                                if "Permission denied" in stderr or "password" in stderr.lower():
                                    error_msg = (
                                        f"SCP 需要 SSH 密钥认证。\n"
                                        f"错误: {stderr}\n\n"
                                        f"解决方案：\n"
                                        f"1. 生成 SSH 密钥: ssh-keygen -t rsa -b 4096\n"
                                        f"2. 复制公钥到服务器: ssh-copy-id {self.config.user}@{self.config.ip}\n"
                                        f"3. 或手动复制: type C:\\Users\\<用户>\\.ssh\\id_rsa.pub | ssh {self.config.user}@{self.config.ip} 'cat >> ~/.ssh/authorized_keys'"
                                    )
                                    self.append_restore_log(f"    ❌ {error_msg}")
                                    raise Exception(error_msg)
                                else:
                                    error_msg = f"上传失败 (退出码: {result.returncode}):\nstdout: {stdout}\nstderr: {stderr}"
                                    self.append_restore_log(f"    ❌ {error_msg}")
                                    raise Exception(error_msg)

                        else:
                            # Linux/Mac: 直接使用 scp
                            self.append_restore_log("    使用 SCP 上传 (Linux/Mac)...")
                            result = subprocess.run(
                                ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                                 temp_tar_path, f"{self.config.user}@{self.config.ip}:/var/lib/docker/tmp/volumes.tar.gz"],
                                capture_output=True,
                                text=True
                            )

                            if result.returncode != 0:
                                error_msg = result.stderr or result.stdout
                                self.append_restore_log(f"    ❌ 上传失败: {error_msg}")
                                raise Exception(f"上传失败: {error_msg}")

                            elapsed = time.time() - start_time
                            self.append_restore_log(f"    ✅ 上传完成 (耗时: {elapsed:.1f}秒)")

                    except Exception as e:
                        elapsed = time.time() - start_time
                        raise Exception(f"上传失败 (耗时: {elapsed:.1f}秒): {str(e)}")

                    # 在服务器上解压
                    self.append_restore_log("  [步骤 6/6] 解压并还原 volumes...")
                    self.append_restore_log("    在服务器上解压 volumes.tar.gz...")
                    extract_cmd = (
                        "cd /opt/ragflowauth/ragflow_compose && "
                        "tar -xzf /var/lib/docker/tmp/volumes.tar.gz && "
                        "rm -f /var/lib/docker/tmp/volumes.tar.gz"
                    )
                    self.append_restore_log(f"    执行: {extract_cmd}")
                    success, output = self.ssh_executor.execute(extract_cmd)
                    if not success:
                        self.append_restore_log(f"    ❌ 解压失败: {output}")
                        raise Exception(f"解压 volumes.tar.gz 失败: {output}")
                    else:
                        self.append_restore_log(f"    ✅ 解压成功")
                        if output:
                            self.append_restore_log(f"    输出: {output}")

                    # 停止 RAGFlow 容器（防止还原时的写入冲突）
                    self.append_restore_log("    停止 RAGFlow 容器（防止还原冲突）...")
                    stop_cmd = "cd /opt/ragflowauth/ragflow_compose && docker compose down"
                    self.append_restore_log(f"    执行: {stop_cmd}")
                    success, output = self.ssh_executor.execute(stop_cmd)
                    if success:
                        self.append_restore_log("    ✅ RAGFlow 容器已停止")
                    else:
                        self.append_restore_log("    ⚠️  停止 RAGFlow 容器时出现警告（可能已停止）")
                        if output:
                            self.append_restore_log(f"    输出: {output}")

                    # 还原 Docker volumes（将 tar.gz 提取到实际的 Docker volume 中）
                    self.append_restore_log("    还原 Docker volumes（提取到实际 volume）...")

                    # 先检查是否有 alpine 镜像
                    self.append_restore_log("    检查 alpine 镜像...")
                    check_alpine_cmd = "docker images | grep alpine || echo 'NOT_FOUND'"
                    success, alpine_output = self.ssh_executor.execute(check_alpine_cmd)
                    if "NOT_FOUND" in alpine_output:
                        self.append_restore_log("    ⚠️  未找到 alpine 镜像，正在拉取（这可能需要几分钟）...")
                        self.append_restore_log("    提示：首次运行会自动拉取 alpine 镜像，请耐心等待")
                        pull_cmd = "docker pull alpine:latest"
                        success, pull_output = self.ssh_executor.execute(pull_cmd)
                        if not success:
                            self.append_restore_log(f"    ❌ 拉取 alpine 镜像失败: {pull_output}")
                            raise Exception(f"拉取 alpine 镜像失败: {pull_output}")
                        self.append_restore_log("    ✅ alpine 镜像拉取完成")
                    else:
                        self.append_restore_log("    ✅ alpine 镜像已存在")

                    # 先列出要还原的 volumes
                    self.append_restore_log("    扫描要还原的 volume 文件...")
                    list_cmd = "ls -1 /opt/ragflowauth/ragflow_compose/volumes/*.tar.gz 2>/dev/null | xargs -n1 basename || echo 'NO_FILES'"
                    success, list_output = self.ssh_executor.execute(list_cmd)
                    if "NO_FILES" in list_output or not list_output.strip():
                        self.append_restore_log("    ⚠️  未找到 volume 备份文件，跳过 volume 还原")
                    else:
                        # 过滤：只保留以 .tar.gz 结尾的行（排除 SSH 错误输出）
                        volume_files = [line.strip() for line in list_output.strip().split('\n')
                                      if line.strip() and line.strip().endswith('.tar.gz')]
                        self.append_restore_log(f"    找到 {len(volume_files)} 个 volume 文件:")
                        for vf in volume_files:
                            self.append_restore_log(f"      - {vf}")

                        # 逐个还原 volume（每个 volume 独立超时）
                        restored_count = 0
                        failed_volumes = []
                        for i, tar_filename in enumerate(volume_files, 1):
                            volume_name = tar_filename.replace('.tar.gz', '')
                            self.append_restore_log(f"\n    [{i}/{len(volume_files)}] 还原 volume: {volume_name}")
                            self.append_restore_log(f"      文件: {tar_filename}")

                            # 检查文件大小（使用 stat 避免 awk 转义问题）
                            size_cmd = f"stat -c %s /opt/ragflowauth/ragflow_compose/volumes/{tar_filename} 2>/dev/null || echo '0'"
                            success, size_output = self.ssh_executor.execute(size_cmd)
                            if success and size_output.strip().isdigit():
                                size_bytes = int(size_output.strip())
                                size_mb = size_bytes / 1024 / 1024
                                self.append_restore_log(f"      大小: {size_mb:.2f} MB")
                            else:
                                self.append_restore_log(f"      大小: (无法获取)")

                            self.append_restore_log(f"      开始解压（预计 1-3 分钟）...")

                            # 还原单个 volume（使用更长的超时：15分钟）
                            # 完全避免引号问题：直接使用 tar 命令，不用 sh -c
                            restore_single_cmd = (
                                f"docker run --rm "
                                f"-v {volume_name}:/data "
                                f"-v /opt/ragflowauth/ragflow_compose/volumes:/backup:ro "
                                f"alpine tar -xzf /backup/{tar_filename} -C /data 2>&1"
                            )
                            self.append_restore_log(f"      执行还原命令（超时 15 分钟）...")
                            # Volume 还原可能需要很长时间，设置 15 分钟超时
                            success, output = self.ssh_executor.execute(restore_single_cmd, timeout_seconds=900)
                            if success:
                                self.append_restore_log(f"      ✅ {volume_name} 还原成功")
                                restored_count += 1
                            else:
                                self.append_restore_log(f"      ⚠️  {volume_name} 还原失败:")
                                self.append_restore_log(f"      错误输出:\n{output}")
                                failed_volumes.append(volume_name)

                        # 汇总结果
                        self.append_restore_log(f"\n    Volume 还原完成:")
                        self.append_restore_log(f"      成功: {restored_count}/{len(volume_files)}")
                        if failed_volumes:
                            self.append_restore_log(f"      失败: {', '.join(failed_volumes)}")
                            if restored_count > 0:
                                self.append_restore_log(f"      ⚠️  部分 volume 还原失败，但 RAGFlow 可能仍能正常工作")
                            else:
                                raise Exception(f"所有 volume 还原失败: {', '.join(failed_volumes)}")

                    self.append_restore_log("  ✅ RAGFlow volumes 还原完成")

                finally:
                    # 删除本地临时文件
                    if os.path.exists(temp_tar_path):
                        os.remove(temp_tar_path)
            else:
                self.append_restore_log("\n[5/7] 跳过 RAGFlow 数据（未找到 volumes）")

            # 6. 启动容器
            self.append_restore_log("\n[6/7] 启动 Docker 容器...")
            self.update_restore_status("正在启动容器...")

            # 停止并删除旧容器（确保使用最新配置重新创建）
            self.append_restore_log("  停止并删除旧容器...")
            success, _ = self.ssh_executor.execute("docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true")
            success, _ = self.ssh_executor.execute("docker rm ragflowauth-backend ragflowauth-frontend 2>/dev/null || true")

            # 获取当前镜像tag
            self.append_restore_log("  获取当前镜像tag...")
            success, output = self.ssh_executor.execute(
                "docker images --format '{{.Tag}}' | grep '^ragflowauth-backend' | head -1 | cut -d: -f2"
            )
            current_tag = output.strip() if success and output.strip() else "latest"
            self.append_restore_log(f"  当前镜像tag: {current_tag}")

            # 使用 remote-deploy.sh 启动容器（包含正确的挂载配置）
            self.append_restore_log("  使用 remote-deploy.sh 重新创建容器...")
            success, output = self.ssh_executor.execute(
                f"cd /tmp && bash remote-deploy.sh --skip-load --tag {current_tag}"
            )

            if success:
                self.append_restore_log("  ✅ RagflowAuth 容器启动成功")
            else:
                self.append_restore_log(f"  ⚠️  容器启动可能有问题: {output}")

            # 启动 RAGFlow 容器（如果还原了 volumes）
            if self.restore_volumes_exists:
                self.append_restore_log("  启动 RAGFlow 容器...")
                success, output = self.ssh_executor.execute(
                    "cd /opt/ragflowauth/ragflow_compose && docker compose up -d"
                )
                self.append_restore_log(f"  {output}")

                if success:
                    self.append_restore_log("  ✅ RAGFlow 容器启动成功")
                else:
                    self.append_restore_log("  ⚠️  RAGFlow 容器启动可能有问题，请检查日志")

                # 等待 RAGFlow 容器启动
                import time
                self.append_restore_log("  等待 RAGFlow 服务完全启动...")
                time.sleep(10)  # RAGFlow 需要更长时间启动
            else:
                self.append_restore_log("  跳过 RAGFlow 容器（未还原数据）")

            # 7. 验证
            self.append_restore_log("\n[7/7] 验证服务状态...")
            self.update_restore_status("正在验证服务...")

            import time
            time.sleep(3)  # 等待容器完全启动

            success, output = self.ssh_executor.execute("docker ps | grep ragflow")
            self.append_restore_log(output)

            # 完成
            self.append_restore_log("\n" + "=" * 60)
            self.append_restore_log("✅ 数据还原完成！")
            self.append_restore_log("=" * 60)
            self.update_restore_status("✅ 还原完成")

            # 显示成功消息
            success_msg = f"数据还原成功！\n\n可以访问以下地址验证：\n"
            success_msg += f"• RagflowAuth 前端: http://{self.config.ip}:3001\n"
            success_msg += f"• RagflowAuth 后端: http://{self.config.ip}:8001\n"
            if self.restore_volumes_exists:
                success_msg += f"• RAGFlow: http://{self.config.ip}\n"
            success_msg += f"\n提示：RAGFlow 服务可能需要 1-2 分钟完全启动"

            msg = f"[INFO] 数据还原成功！\n{success_msg}"
            print(msg)
            log_to_file(msg)
            messagebox.showinfo("还原完成", success_msg)

        except Exception as e:
            error_msg = f"还原失败: {str(e)}"
            self.append_restore_log(f"\n❌ {error_msg}")
            self.update_restore_status("❌ 还原失败")
            msg = f"[ERROR] {error_msg}"
            print(msg)
            log_to_file(msg, "ERROR")
            messagebox.showerror("还原失败", error_msg)

        finally:
            # 恢复按钮状态和停止进度条
            self.stop_restore_progress()


def main():
    """主函数"""
    # 记录应用启动
    log_to_file("=" * 80)
    log_to_file(f"RagflowAuth 工具启动")
    log_to_file(f"日志文件: {LOG_FILE}")
    log_to_file("=" * 80)

    try:
        root = tk.Tk()
        app = RagflowAuthTool(root)
        root.mainloop()
    except Exception as e:
        error_msg = f"未捕获的异常: {str(e)}"
        print(error_msg)
        log_to_file(error_msg, "ERROR")
        import traceback
        log_to_file(traceback.format_exc(), "ERROR")
        raise


if __name__ == "__main__":
    main()
