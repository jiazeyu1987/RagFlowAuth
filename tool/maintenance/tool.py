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
import time
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

# ==================== 环境配置 ====================
ENVIRONMENTS = {
    "正式服务器": {
        "ip": "172.30.30.57",
        "user": "root",
        "description": "生产环境"
    },
    "测试服务器": {
        "ip": "172.30.30.58",
        "user": "root",
        "description": "测试环境（密码：KDLyx2021）"
    }
}


class ServerConfig:
    """服务器配置"""

    def __init__(self):
        self.ip = "172.30.30.57"
        self.user = "root"
        self.environment = "正式服务器"
        self.load_config()

    def load_config(self):
        """从文件加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            if key == "SERVER_IP":
                                self.ip = value
                            elif key == "SERVER_USER":
                                self.user = value
                            elif key == "ENVIRONMENT":
                                self.environment = value
            except Exception as e:
                msg = f"加载配置失败: {e}"
                print(msg)
                log_to_file(msg, "ERROR")

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                f.write(f"ENVIRONMENT={self.environment}\n")
                f.write(f"SERVER_IP={self.ip}\n")
                f.write(f"SERVER_USER={self.user}\n")
        except Exception as e:
            msg = f"保存配置失败: {e}"
            print(msg)
            log_to_file(msg, "ERROR")

    def set_environment(self, env_name):
        """设置环境"""
        if env_name in ENVIRONMENTS:
            self.environment = env_name
            env_config = ENVIRONMENTS[env_name]
            self.ip = env_config["ip"]
            self.user = env_config["user"]
            return True
        return False


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
        # SSH 选项：
        # - BatchMode=yes: 避免等待密码输入
        # - ConnectTimeout=10: 连接超时 10 秒
        # - ControlMaster=no: 禁用连接复用（避免通道冲突）
        full_command = (
            f'ssh -o BatchMode=yes -o ConnectTimeout=10 -o ControlMaster=no '
            f'{self.user}@{self.ip} "{escaped_command}"'
        )

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

    def execute_with_retry(self, command, max_retries=3, callback=None, timeout_seconds=30):
        """执行 SSH 命令，遇到连接错误时自动重试

        Args:
            command: 要执行的命令
            max_retries: 最大重试次数
            callback: 可选的回调函数
            timeout_seconds: 每次尝试的超时时间
        """
        last_error = None

        for attempt in range(max_retries):
            success, output = self.execute(command, callback=callback, timeout_seconds=timeout_seconds)

            # 如果成功，或者不是连接错误，直接返回
            if success:
                return True, output

            # 检查是否是连接相关的错误
            connection_errors = [
                "IO is still pending on closed socket",
                "channel free",
                "unknown channel",
                "Connection reset",
                "Connection timed out"
            ]

            is_connection_error = any(err in output for err in connection_errors)

            if not is_connection_error:
                # 不是连接错误，不再重试
                return False, output

            # 是连接错误，记录并重试
            last_error = output
            if attempt < max_retries - 1:
                log_to_file(f"[SSH] 连接错误，{attempt + 1}/{max_retries} 次重试...", "WARNING")
                import time
                time.sleep(1)  # 等待 1 秒后重试

        # 所有重试都失败
        log_to_file(f"[SSH] 所有重试均失败，最后错误: {last_error}", "ERROR")
        return False, last_error


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

        # 输出区域（已删除）
        # self.output = scrolledtext.ScrolledText(
        #     self, height=8, width=50, state=tk.DISABLED, font=("Consolas", 9)
        # )

    def on_click(self):
        """按钮点击事件"""
        if self.command:
            # 不显示输出区域（已删除）
            # self.output.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            # self.output.config(state=tk.NORMAL)
            # self.output.delete(1.0, tk.END)
            # self.output.config(state=tk.DISABLED)

            # 在后台线程执行
            thread = threading.Thread(target=self.command, daemon=True)
            thread.start()

    def append_output(self, text):
        """追加输出（已禁用）"""
        # 输出区域已删除，只记录到日志文件
        # self.output.config(state=tk.NORMAL)
        # self.output.insert(tk.END, text)
        # self.output.see(tk.END)
        # self.output.config(state=tk.DISABLED)
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

        # 根据当前环境初始化字段状态
        self._init_field_states()

    def show_text_window(self, title: str, content: str):
        """
        显示可复制文本的窗口，支持颜色标记

        Args:
            title: 窗口标题
            content: 要显示的内容，支持 [RED]...[/RED] 和 [GREEN]...[/GREEN] 标记
        """
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("800x600")

        # 创建文本框
        text_widget = scrolledtext.ScrolledText(
            window,
            wrap=tk.WORD,
            font=("Courier New", 10),
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)

        # 配置颜色标签
        text_widget.tag_config("red", foreground="red")
        text_widget.tag_config("green", foreground="green")

        # 解析颜色标记并插入文本
        self._insert_colored_text(text_widget, content)

        text_widget.config(state=tk.DISABLED)  # 只读模式

        # 添加按钮框架
        button_frame = ttk.Frame(window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # 复制按钮
        ttk.Button(
            button_frame,
            text="复制全部",
            command=lambda: self._copy_to_clipboard(content)
        ).pack(side=tk.LEFT, padx=5)

        # 关闭按钮
        ttk.Button(
            button_frame,
            text="关闭",
            command=window.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def _insert_colored_text(self, text_widget, content: str):
        """
        解析颜色标记并插入文本到文本框

        支持的标记：
        - [RED]...[/RED] - 红色文本
        - [GREEN]...[/GREEN] - 绿色文本
        """
        import re

        # 定义颜色标记的正则表达式
        pattern = r'\[(RED|GREEN)\](.*?)\[\/\1\]'

        pos = 0
        for match in re.finditer(pattern, content, re.DOTALL):
            # 插入标记之前的普通文本
            if match.start() > pos:
                text_widget.insert(tk.END, content[pos:match.start()])

            # 插入带颜色的文本
            color = match.group(1).lower()
            colored_text = match.group(2)
            text_widget.insert(tk.END, colored_text, color)

            pos = match.end()

        # 插入剩余的普通文本
        if pos < len(content):
            text_widget.insert(tk.END, content[pos:])

    def _copy_to_clipboard(self, content: str):
        """复制内容到剪贴板（去除颜色标记）"""
        import re

        # 去除颜色标记后再复制
        clean_content = re.sub(r'\[(RED|GREEN)\](.*?)\[\/\1\]', r'\2', content, flags=re.DOTALL)

        self.root.clipboard_clear()
        self.root.clipboard_append(clean_content)
        self.status_bar.config(text="已复制到剪贴板")

    def setup_ui(self):
        """设置 UI"""
        # 配置按钮样式
        style = ttk.Style()
        style.configure("Large.TButton", font=("Arial", 12, "bold"), padding=10)

        # 顶部配置区域
        config_frame = ttk.LabelFrame(self.root, text="服务器配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # 环境选择下拉菜单
        ttk.Label(config_frame, text="环境:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.env_var = tk.StringVar(value=self.config.environment)
        env_combo = ttk.Combobox(
            config_frame,
            textvariable=self.env_var,
            values=list(ENVIRONMENTS.keys()),
            state="readonly",
            width=15
        )
        env_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        env_combo.bind("<<ComboboxSelected>>", self.on_environment_changed)

        # 当前IP显示（根据环境可编辑或只读）
        ttk.Label(config_frame, text="服务器 IP:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.ip_var = tk.StringVar(value=self.config.ip)
        self.ip_entry = ttk.Entry(config_frame, textvariable=self.ip_var, width=18)
        self.ip_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        # 当前用户显示（根据环境可编辑或只读）
        ttk.Label(config_frame, text="用户名:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.user_var = tk.StringVar(value=self.config.user)
        self.user_entry = ttk.Entry(config_frame, textvariable=self.user_var, width=12)
        self.user_entry.grid(row=0, column=5, sticky=tk.W, padx=(0, 20))

        # 保存按钮
        save_btn = ttk.Button(config_frame, text="保存配置", command=self.save_config)
        save_btn.grid(row=0, column=6, padx=(5, 0))

        # 测试连接按钮
        test_btn = ttk.Button(config_frame, text="测试连接", command=self.test_connection)
        test_btn.grid(row=0, column=7, padx=(5, 0))

        # Notebook（选项卡）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建选项卡
        self.create_tools_tab()
        self.create_web_links_tab()
        self.create_backup_tab()
        self.create_restore_tab()
        self.create_backup_files_tab()  # 新增：备份文件管理
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
                "desc": "清理服务器上未使用的 Docker 镜像，释放磁盘空间（仅保留当前运行的镜像）",
                "cmd": "__cleanup_docker_images__"
            },
            {
                "title": "挂载 Windows 共享",
                "desc": "挂载 Windows 网络共享到服务器（//192.168.112.72/backup → /mnt/replica）",
                "cmd": "__mount_windows_share__"
            },
            {
                "title": "卸载 Windows 共享",
                "desc": "卸载 Windows 网络共享（停止自动备份同步）",
                "cmd": "__unmount_windows_share__"
            },
            {
                "title": "检查挂载状态",
                "desc": "检查 Windows 共享挂载状态和可用空间",
                "cmd": "__check_mount_status__"
            },
            {
                "title": "快速部署",
                "desc": "快速部署到服务器（使用 Windows 本地构建的镜像）",
                "cmd": "quick-deploy"
            },
            {
                "title": "快速重启容器",
                "desc": "使用现有镜像快速重启容器（自动检测镜像标签并修复挂载）",
                "cmd": "__smart_quick_restart__"
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
                "cmd": "docker start ragflowauth-backend ragflow-frontend"
            },
        ]

        # 创建网格布局容器
        grid_frame = ttk.Frame(scrollable_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for i, tool in enumerate(tools):
            row = i // 3  # 每行3个按钮
            col = i % 3   # 列索引

            # 创建按钮框架（包含按钮和注释）
            tool_frame = ttk.Frame(grid_frame, relief="ridge", borderwidth=1)
            tool_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # 配置网格权重，使列均匀分布
            grid_frame.columnconfigure(col, weight=1)
            grid_frame.rowconfigure(row, weight=1)

            # 工具按钮（充满框架宽度，放大字体和尺寸）
            btn = ttk.Button(
                tool_frame,
                text=tool['title'],
                command=lambda cmd=tool["cmd"]: self.execute_ssh_command(cmd),
                style="Large.TButton"
            )
            btn.pack(fill=tk.X, expand=True, pady=(8, 4), padx=8)

            # 工具注释说明（充满框架宽度，放大字体）
            desc_label = ttk.Label(
                tool_frame,
                text=tool['desc'],
                wraplength=250,
                foreground="gray",
                font=("Arial", 10),
                justify="left",
                anchor="w"
            )
            desc_label.pack(fill=tk.BOTH, expand=True, pady=(0, 8), padx=8)

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
            text="Portainer - Docker 容器管理平台 (HTTPS 端口 9002)\n"
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

    def create_backup_files_tab(self):
        """创建备份文件管理选项卡"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  备份文件  ")

        # 标题
        title_label = ttk.Label(
            tab,
            text="服务器备份文件管理",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=10)

        # 说明
        desc_label = ttk.Label(
            tab,
            text="管理服务器上的备份文件，支持查看和删除两个位置的备份：\n"
                 "• /opt/ragflowauth/data/backups/ - 主要存储 auth.db\n"
                 "• /opt/ragflowauth/backups/ - 主要存储 volumes/*.tar.gz",
            foreground="gray",
            justify=tk.LEFT
        )
        desc_label.pack(pady=(0, 10), padx=20)

        # 操作按钮区域
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        ttk.Button(button_frame, text="刷新文件列表", command=self.refresh_backup_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除选中文件", command=self.delete_selected_backup_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空旧备份（30天前）", command=self.cleanup_old_backups).pack(side=tk.LEFT, padx=5)

        # 创建左右两个区域的 PanedWindow
        paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        # 左侧：/opt/ragflowauth/data/backups/
        left_frame = ttk.LabelFrame(paned, text="/opt/ragflowauth/data/backups/ (auth.db)")
        paned.add(left_frame, weight=1)

        # Treeview for left side
        left_columns = ("name", "size", "date")
        self.left_tree = ttk.Treeview(left_frame, columns=left_columns, show="tree headings", selectmode="extended")
        self.left_tree.heading("#0", text="文件名")
        self.left_tree.heading("size", text="大小")
        self.left_tree.heading("date", text="日期")

        self.left_tree.column("#0", width=250)
        self.left_tree.column("size", width=100)
        self.left_tree.column("date", width=150)

        left_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.left_tree.yview)
        self.left_tree.configure(yscrollcommand=left_scrollbar.set)

        self.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击事件
        self.left_tree.bind("<Double-1>", lambda _: self.show_backup_file_details("left"))

        # 右侧：/opt/ragflowauth/backups/
        right_frame = ttk.LabelFrame(paned, text="/opt/ragflowauth/backups/ (volumes)")
        paned.add(right_frame, weight=1)

        # Treeview for right side
        right_columns = ("name", "size", "date")
        self.right_tree = ttk.Treeview(right_frame, columns=right_columns, show="tree headings", selectmode="extended")
        self.right_tree.heading("#0", text="文件名")
        self.right_tree.heading("size", text="大小")
        self.right_tree.heading("date", text="日期")

        self.right_tree.column("#0", width=250)
        self.right_tree.column("size", width=100)
        self.right_tree.column("date", width=150)

        right_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_tree.yview)
        self.right_tree.configure(yscrollcommand=right_scrollbar.set)

        self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击事件
        self.right_tree.bind("<Double-1>", lambda _: self.show_backup_file_details("right"))

        # 状态标签
        self.backup_files_status = ttk.Label(tab, text="点击'刷新文件列表'加载数据", relief=tk.SUNKEN)
        self.backup_files_status.pack(fill=tk.X, padx=20, pady=(0, 10))

    def refresh_backup_files(self):
        """刷新备份文件列表"""
        self.backup_files_status.config(text="正在加载文件列表...")
        self.root.update()

        # 确保 SSH 执行器已初始化
        self.update_ssh_executor()

        def load_files():
            # 获取两个目录的文件列表
            left_files = self._get_backup_files("/opt/ragflowauth/data/backups/")
            right_files = self._get_backup_files("/opt/ragflowauth/backups/")

            # 更新UI（在主线程中）
            self.root.after(0, lambda: self._update_file_trees(left_files, right_files))

        # 在后台线程中执行
        thread = threading.Thread(target=load_files, daemon=True)
        thread.start()

    def _get_backup_files(self, directory):
        """获取指定目录的备份文件列表"""
        cmd = f'ls -lh --time-style=long-iso {directory} 2>/dev/null | grep "^d" | tail -20'
        success, output = self.ssh_executor.execute(cmd)

        if not success:
            return []

        files = []
        for line in output.split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 7:
                name = parts[8] if len(parts) > 8 else parts[-1]
                # 跳过 . 和 ..
                if name in ['.', '..']:
                    continue
                date = f"{parts[5]} {parts[6]}" if len(parts) > 6 else ""
                files.append({
                    'name': name,
                    'path': f"{directory}/{name}",
                    'date': date
                })

        return sorted(files, key=lambda x: x['name'], reverse=True)

    def _update_file_trees(self, left_files, right_files):
        """更新文件树视图"""
        # 清空现有内容
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)

        # 插入左侧文件
        for file in left_files:
            self.left_tree.insert("", "end", text=file['name'],
                                   values=(file['name'], self._get_file_size(file['path']), file['date']))

        # 插入右侧文件
        for file in right_files:
            self.right_tree.insert("", "end", text=file['name'],
                                    values=(file['name'], self._get_file_size(file['path']), file['date']))

        left_count = len(left_files)
        right_count = len(right_files)
        self.backup_files_status.config(text=f"加载完成: data/backups/ ({left_count}个文件), backups/ ({right_count}个文件)")

    def _get_file_size(self, path):
        """获取文件或目录大小"""
        # 获取目录大小
        cmd = f"du -sh {path} 2>/dev/null | cut -f1"
        success, output = self.ssh_executor.execute(cmd)
        if success and output.strip():
            return output.strip().split('\n')[0]
        return "N/A"

    def show_backup_file_details(self, side):
        """显示备份文件详情"""
        tree = self.left_tree if side == "left" else self.right_tree
        selection = tree.selection()
        if not selection:
            return

        item = selection[0]
        values = tree.item(item, 'values')
        file_name = values[0]

        # 获取详细内容
        base_path = "/opt/ragflowauth/data/backups/" if side == "left" else "/opt/ragflowauth/backups/"
        cmd = f"ls -lh {base_path}{file_name}/ 2>/dev/null"
        success, output = self.ssh_executor.execute(cmd)

        if success:
            # 显示详情窗口
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"备份详情: {file_name}")
            detail_window.geometry("600x400")

            text_widget = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD, font=("Consolas", 10))
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert("1.0", output)
            text_widget.config(state=tk.DISABLED)
        else:
            messagebox.showerror("错误", f"无法获取文件详情: {file_name}")

    def delete_selected_backup_files(self):
        """删除选中的备份文件"""
        # 获取选中的文件
        left_selected = self.left_tree.selection()
        right_selected = self.right_tree.selection()

        if not left_selected and not right_selected:
            messagebox.showwarning("提示", "请先选择要删除的文件")
            return

        # 收集要删除的文件
        files_to_delete = []

        for item in left_selected:
            values = self.left_tree.item(item, 'values')
            file_name = values[0]
            files_to_delete.append(("/opt/ragflowauth/data/backups/", file_name))

        for item in right_selected:
            values = self.right_tree.item(item, 'values')
            file_name = values[0]
            files_to_delete.append(("/opt/ragflowauth/backups/", file_name))

        # 确认删除
        file_list = "\n".join([f"  {path}{name}" for path, name in files_to_delete])
        confirm = messagebox.askyesno("确认删除",
                                       f"确定要删除以下 {len(files_to_delete)} 个备份吗？\n\n{file_list}")

        if not confirm:
            return

        # 执行删除
        self.backup_files_status.config(text=f"正在删除 {len(files_to_delete)} 个文件...")
        self.root.update()

        def delete_files():
            deleted = []
            failed = []

            for base_path, file_name in files_to_delete:
                full_path = f"{base_path}{file_name}"
                cmd = f"rm -rf {full_path}"
                success, _ = self.ssh_executor.execute(cmd)

                if success:
                    deleted.append(file_name)
                else:
                    failed.append(file_name)

            # 更新UI
            self.root.after(0, lambda: self._delete_complete(deleted, failed))

        thread = threading.Thread(target=delete_files, daemon=True)
        thread.start()

    def _delete_complete(self, deleted, failed):
        """删除完成回调"""
        if deleted:
            msg = f"成功删除 {len(deleted)} 个文件"
            if failed:
                msg += f"\n失败 {len(failed)} 个文件"

            self.backup_files_status.config(text=msg)
            messagebox.showinfo("删除完成", msg)

            # 刷新列表
            self.refresh_backup_files()
        elif failed:
            self.backup_files_status.config(text="删除失败")
            messagebox.showerror("错误", f"删除失败:\n" + "\n".join(failed))

    def cleanup_old_backups(self):
        """清理30天前的旧备份"""
        confirm = messagebox.askyesno("确认清理",
                                       "确定要删除30天前的所有备份吗？\n\n"
                                       "这将删除以下两个目录中30天前的文件：\n"
                                       "• /opt/ragflowauth/data/backups/\n"
                                       "• /opt/ragflowauth/backups/")
        if not confirm:
            return

        self.backup_files_status.config(text="正在清理旧备份...")
        self.root.update()

        def cleanup():
            # 清理两个目录
            cmd1 = "find /opt/ragflowauth/data/backups/ -maxdepth 1 -type d -mtime +30 -exec rm -rf {} + 2>/dev/null"
            cmd2 = "find /opt/ragflowauth/backups/ -maxdepth 1 -type d -mtime +30 -exec rm -rf {} + 2>/dev/null"

            self.ssh_executor.execute(cmd1)
            self.ssh_executor.execute(cmd2)

            # 刷新列表
            self.root.after(0, self.refresh_backup_files)
            self.root.after(0, lambda: messagebox.showinfo("清理完成", "30天前的旧备份已删除"))

        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()

    def mount_windows_share(self):
        """挂载 Windows 网络共享"""
        if not self.update_ssh_executor():
            self.show_text_window("错误", "[RED]请先配置服务器信息[/RED]")
            return

        def do_mount():
            try:
                import subprocess
                import os

                script_path = os.path.join(os.path.dirname(__file__), "scripts", "mount-windows-share.ps1")

                print(f"[MOUNT] 调用 PowerShell 脚本: {script_path}", flush=True)
                self.status_bar.config(text="正在挂载 Windows 共享...")
                self.root.update()

                # 执行 PowerShell 脚本
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=180  # 3分钟超时
                )

                # 读取日志文件
                log_file = r"C:\Users\BJB110\AppData\Local\Temp\mount_windows_share.log"
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()

                if result.returncode == 0:
                    print("[MOUNT] ✓ 挂载成功", flush=True)
                    self.root.after(0, lambda: self.status_bar.config(text="挂载成功"))
                    self.root.after(0, lambda: self.show_text_window("成功", f"[GREEN]Windows 共享挂载成功！[/GREEN]\n\n{log_content}"))
                else:
                    print(f"[MOUNT] ✗ 挂载失败\n{result.stderr}", flush=True)
                    self.root.after(0, lambda: self.status_bar.config(text="挂载失败"))
                    self.root.after(0, lambda: self.show_text_window("错误", f"[RED]挂载失败[/RED]\n\n{log_content}"))

            except Exception as e:
                print(f"[MOUNT] ERROR: {str(e)}", flush=True)
                self.root.after(0, lambda: self.show_text_window("错误", f"[RED]挂载过程出错:\n\n{str(e)}[/RED]"))
                self.root.after(0, lambda: self.status_bar.config(text="挂载失败"))

        # 在后台线程执行
        thread = threading.Thread(target=do_mount, daemon=True)
        thread.start()


    def _pre_mount_diagnostic(self):
        """挂载前诊断，检查网络、挂载点、进程占用等"""
        try:
            diag_lines = []

            # 1. 检查挂载点目录
            print("[DIAG] 1. 检查挂载点目录...", flush=True)
            success, output = self.ssh_executor.execute("ls -ld /mnt/replica 2>&1")
            diag_lines.append(f"1. 挂载点目录: {output.strip() if output.strip() else '不存在'}")

            # 2. 检查是否有残留挂载
            print("[DIAG] 2. 检查残留挂载...", flush=True)
            success, output = self.ssh_executor.execute("mount | grep /mnt/replica")
            if success and output.strip():
                diag_lines.append(f"2. [RED]✗ 发现残留挂载:[/RED]\n{output.strip()}")
                diag_lines.append("   建议: 先使用 '卸载 Windows 共享' 工具")
            else:
                diag_lines.append("2. [GREEN]✓ 无残留挂载[/GREEN]")

            # 3. 检查进程占用
            print("[DIAG] 3. 检查进程占用...", flush=True)
            success, output = self.ssh_executor.execute("fuser /mnt/replica 2>&1 || echo '无进程占用'")
            if "no process" in output.lower() or "无进程占用" in output:
                diag_lines.append("3. [GREEN]✓ 无进程占用挂载点[/GREEN]")
            else:
                diag_lines.append(f"3. [RED]✗ 进程占用:[/RED]\n{output.strip()}")

            # 4. 测试 ICMP 连通性
            print("[DIAG] 4. 测试 ICMP 连通性...", flush=True)
            success, output = self.ssh_executor.execute("ping -c 2 -W 2 192.168.112.72 2>&1")
            if "100% packet loss" in output or "unreachable" in output.lower():
                diag_lines.append("4. [RED]✗ ICMP 不可达（ping 失败）[/RED]")
            elif "0% packet loss" in output or "100% packet loss" not in output:
                diag_lines.append("4. [GREEN]✓ ICMP 可达（ping 成功）[/GREEN]")
            else:
                diag_lines.append(f"4. [YELLOW]⚠ ICMP 部分可达:[/YELLOW]\n{output.strip()[:100]}")

            # 5. 测试 TCP 445 端口（SMB）
            print("[DIAG] 5. 测试 TCP 445 端口...", flush=True)
            port_test_cmd = (
                "timeout 3 bash -c 'echo > /dev/tcp/192.168.112.72/445' 2>&1 "
                "&& echo '端口可达' || echo '端口不可达'"
            )
            success, output = self.ssh_executor.execute(port_test_cmd)
            if "端口可达" in output:
                diag_lines.append("5. [GREEN]✓ TCP 445 端口可达（SMB 服务可用）[/GREEN]")
            else:
                diag_lines.append("5. [RED]✗ TCP 445 端口不可达（SMB 服务不可用）[/RED]")
                diag_lines.append("   可能原因: 防火墙阻止、SMB 服务未启用、Windows 主机离线")

            # 6. 检查凭据文件
            print("[DIAG] 6. 检查凭据文件...", flush=True)
            success, output = self.ssh_executor.execute("ls -la /root/.smbcredentials 2>&1")
            if success and ".smbcredentials" in output:
                diag_lines.append("6. [GREEN]✓ 凭据文件存在[/GREEN]")
            else:
                diag_lines.append("6. [YELLOW]⚠ 凭据文件不存在（将自动创建）[/YELLOW]")

            # 7. 检查是否有 cifs-utils
            print("[DIAG] 7. 检查 cifs-utils...", flush=True)
            success, output = self.ssh_executor.execute("which mount.cifs 2>&1")
            if success:
                diag_lines.append("7. [GREEN]✓ cifs-utils 已安装[/GREEN]")
            else:
                diag_lines.append("7. [RED]✗ cifs-utils 未安装[/RED]")
                diag_lines.append("   修复: yum install cifs-utils -y")

            # 总结
            print("[DIAG] 诊断完成", flush=True)
            return "\n".join(diag_lines)

        except Exception as e:
            error_msg = f"诊断过程出错: {str(e)}"
            print(f"[DIAG] ERROR: {error_msg}", flush=True)
            return error_msg

    def _get_mount_diagnostic_info(self):
        """收集挂载诊断信息"""
        try:
            diag_lines = []

            # 检查挂载点状态
            success, output = self.ssh_executor.execute("mount | grep /mnt/replica")
            if success and output.strip():
                diag_lines.append(f"当前挂载状态:\n{output}\n")
            else:
                diag_lines.append("当前状态: /mnt/replica 未挂载\n")

            # 检查挂载点目录
            success, output = self.ssh_executor.execute("ls -ld /mnt/replica 2>&1")
            diag_lines.append(f"挂载点目录:\n{output}\n")

            # 检查凭据文件
            success, output = self.ssh_executor.execute("ls -la /root/.smbcredentials 2>&1")
            diag_lines.append(f"凭据文件:\n{output}\n")

            # 测试 Windows 主机连接
            success, output = self.ssh_executor.execute("ping -c 1 -W 2 192.168.112.72 2>&1 || echo 'unreachable'")
            if "unreachable" in output.lower() or "100% packet loss" in output:
                diag_lines.append("[RED]✗ Windows 主机 (192.168.112.72) 不可达[/RED]\n")
            else:
                diag_lines.append("[GREEN]✓ Windows 主机 (192.168.112.72) 可达[/GREEN]\n")

            # 检查是否已有挂载项在 /etc/fstab
            success, output = self.ssh_executor.execute("grep /mnt/replica /etc/fstab 2>&1 || echo '未找到 fstab 条目'")
            diag_lines.append(f"/etc/fstab 条目:\n{output}\n")

            return "\n".join(diag_lines)
        except Exception as e:
            return f"收集诊断信息时出错: {str(e)}"

    def unmount_windows_share(self):
        """卸载 Windows 网络共享"""
        if not self.update_ssh_executor():
            self.show_text_window("错误", "[RED]请先配置服务器信息[/RED]")
            return

        # 去掉确认弹框，直接执行卸载
        print("[UNMOUNT] 开始卸载流程", flush=True)

        def do_unmount():
            try:
                import subprocess
                import os

                script_path = os.path.join(os.path.dirname(__file__), "scripts", "unmount-windows-share.ps1")

                print(f"[UNMOUNT] 调用 PowerShell 脚本: {script_path}", flush=True)
                self.status_bar.config(text="正在卸载 Windows 共享...")
                self.root.update()

                # 执行 PowerShell 脚本
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120  # 2分钟超时
                )

                # 读取日志文件
                log_file = r"C:\Users\BJB110\AppData\Local\Temp\unmount_windows_share.log"
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()

                if result.returncode == 0:
                    print("[UNMOUNT] ✓ 卸载成功", flush=True)
                    self.root.after(0, lambda: self.status_bar.config(text="卸载成功"))
                    self.root.after(0, lambda: self.show_text_window("卸载成功", f"[GREEN]Windows 网络共享已成功卸载！[/GREEN]\n\n{log_content}"))
                else:
                    print(f"[UNMOUNT] ✗ 卸载失败\n{result.stderr}", flush=True)
                    self.root.after(0, lambda: self.status_bar.config(text="卸载失败"))
                    self.root.after(0, lambda: self.show_text_window("错误", f"[RED]卸载失败[/RED]\n\n{log_content}"))

            except Exception as e:
                print(f"[UNMOUNT] ERROR: {str(e)}", flush=True)
                self.root.after(0, lambda: self.show_text_window("错误", f"[RED]卸载过程出错:\n\n{str(e)}[/RED]"))
                self.root.after(0, lambda: self.status_bar.config(text="卸载失败"))

        # 在后台线程执行
        thread = threading.Thread(target=do_unmount, daemon=True)
        thread.start()

    def check_mount_status(self):
        """检查 Windows 共享挂载状态"""
        if not self.update_ssh_executor():
            self.show_text_window("错误", "[RED]请先配置服务器信息[/RED]")
            return

        def do_check():
            try:
                import subprocess
                import os

                script_path = os.path.join(os.path.dirname(__file__), "scripts", "check-mount-status.ps1")

                print("[CHECK] 调用 PowerShell 脚本: {script_path}", flush=True)
                self.status_bar.config(text="正在检查挂载状态...")
                self.root.update()

                # 执行 PowerShell 脚本
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120  # 2分钟超时
                )

                # 读取日志文件
                log_file = r"C:\Users\BJB110\AppData\Local\Temp\check_mount_status.log"
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()

                    # 解析挂载状态并在第一行高亮显示（只读取最新的摘要）
                    status_line = ""
                    # 查找最后一条 [Summary] 行
                    lines = log_content.split('\n')
                    for i in range(len(lines) - 1, -1, -1):
                        line = lines[i].strip()
                        if "[Summary] Mount Status: Mounted" in line:
                            status_line = "[GREEN]挂载状态: 已连接 (Mounted)[/GREEN]\n\n"
                            break
                        elif "[Summary] Mount Status: Not Mounted" in line:
                            status_line = "[RED]挂载状态: 未连接 (Not Mounted)[/RED]\n\n"
                            break

                    # 如果没找到Summary，尝试查找 Status: 行
                    if not status_line:
                        for i in range(len(lines) - 1, -1, -1):
                            line = lines[i].strip()
                            if "Status: Mounted (OK)" in line:
                                status_line = "[GREEN]挂载状态: 已连接 (Mounted)[/GREEN]\n\n"
                                break
                            elif "Status: Not Mounted" in line:
                                status_line = "[RED]挂载状态: 未连接 (Not Mounted)[/RED]\n\n"
                                break

                    if status_line:
                        # 将状态行放在最前面
                        log_content = status_line + log_content

                if result.returncode == 0:
                    print("[CHECK] ✓ 检查完成", flush=True)
                    self.root.after(0, lambda: self.status_bar.config(text="检查完成"))
                    self.root.after(0, lambda: self.show_text_window("挂载状态检查", log_content))
                else:
                    print(f"[CHECK] ✗ 检查失败\n{result.stderr}", flush=True)
                    self.root.after(0, lambda: self.status_bar.config(text="检查失败"))
                    self.root.after(0, lambda: self.show_text_window("错误", f"[RED]检查失败[/RED]\n\n{log_content}"))

            except Exception as e:
                print(f"[CHECK] ERROR: {str(e)}", flush=True)
                self.root.after(0, lambda: self.show_text_window("错误", f"[RED]检查过程出错:\n\n{str(e)}[/RED]"))
                self.root.after(0, lambda: self.status_bar.config(text="检查失败"))

        # 在后台线程执行
        thread = threading.Thread(target=do_check, daemon=True)
        thread.start()

    def on_environment_changed(self, event=None):
        """环境切换回调"""
        _ = event  # Callback参数，未使用
        env_name = self.env_var.get()

        # 预定义环境
        if self.config.set_environment(env_name):
            # 更新UI显示（字段保持可编辑状态）
            self.ip_var.set(self.config.ip)
            self.user_var.set(self.config.user)
            self.status_bar.config(text=f"已切换到: {env_name}（可以手动修改IP）")
            msg = f"[INFO] 环境已切换到: {env_name} ({self.config.user}@{self.config.ip})"
            print(msg)
            log_to_file(msg)
        else:
            messagebox.showerror("错误", f"未知的环境: {env_name}")

    def _init_field_states(self):
        """初始化字段状态（始终可编辑）"""
        # 字段始终可编辑，用户可以手动修改任何环境的IP
        self.ip_entry.config(state="normal")
        self.user_entry.config(state="normal")

    def save_config(self):
        """保存配置"""
        self.config.ip = self.ip_var.get()
        self.config.user = self.user_var.get()
        self.config.environment = self.env_var.get()
        self.config.save_config()
        self.status_bar.config(text="配置已保存")
        msg = f"[INFO] 配置已保存: {self.config.environment} ({self.config.user}@{self.config.ip})"
        print(msg)
        log_to_file(msg)
        messagebox.showinfo("成功", f"配置已保存\n\n环境: {self.config.environment}\n服务器: {self.config.user}@{self.config.ip}")

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
        """更新 SSH 执行器，返回 True 表示成功，False 表示失败"""
        self.config.ip = self.ip_var.get().strip()
        self.config.user = self.user_var.get().strip()

        # 检查必要的配置
        if not self.config.ip:
            print("[ERROR] 服务器 IP 未配置")
            return False

        if not self.config.user:
            print("[ERROR] 用户名未配置")
            return False

        self.ssh_executor = SSHExecutor(self.config.ip, self.config.user)
        return True

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

        # 特殊处理：智能快速重启（自动检测镜像标签）
        if command == "__smart_quick_restart__":
            self.smart_quick_restart()
            return

        # 特殊处理：清理 Docker 镜像（仅保留当前运行的镜像）
        if command == "__cleanup_docker_images__":
            self.cleanup_docker_images()
            return

        # 特殊处理：挂载 Windows 共享
        if command == "__mount_windows_share__":
            self.mount_windows_share()
            return

        # 特殊处理：卸载 Windows 共享
        if command == "__unmount_windows_share__":
            self.unmount_windows_share()
            return

        # 特殊处理：检查挂载状态
        if command == "__check_mount_status__":
            self.check_mount_status()
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
                # 不显示弹窗，只更新状态栏和记录日志
                # messagebox.showinfo("成功", f"命令执行成功！\n\n输出:\n{output}")
            else:
                self.status_bar.config(text="命令执行失败")
                msg = f"[ERROR] 命令执行失败！\n错误: {output}"
                print(msg)
                log_to_file(msg, "ERROR")
                # 不显示弹窗，只更新状态栏和记录日志
                # messagebox.showerror("失败", f"命令执行失败！\n\n错误: {output}")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def run_quick_deploy(self):
        """执行快速部署（7步部署流程）"""
        self.status_bar.config(text="Step 1/7: 停止服务器容器...")

        def execute():
            try:
                # 读取配置（端口、网络、路径等）
                import json
                config_path = Path(__file__).parent / "tool" / "scripts" / "deploy-config.json"
                if not config_path.exists():
                    raise FileNotFoundError(f"配置文件不存在: {config_path}")

                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 使用当前选择的服务器配置（从界面获取）
                server_host = self.config.ip
                server_user = self.config.user

                # 从配置文件读取端口、网络、路径等
                frontend_port = config['docker']['frontend_port']
                backend_port = config['docker']['backend_port']
                network_name = config['docker']['network']
                data_dir = config['paths']['data_dir']

                log_to_file(f"[部署目标] 服务器: {server_user}@{server_host}")
                log_to_file(f"[部署目标] 环境: {self.config.environment}")

                # 生成时间戳标签
                from datetime import datetime
                tag = datetime.now().strftime("%Y-%m-%d-%H%M%S")
                frontend_image = f"ragflowauth-frontend:{tag}"
                backend_image = f"ragflowauth-backend:{tag}"

                repo_root = Path(__file__).parent
                temp_dir = repo_root / "tool" / "scripts" / "temp"

                # ========== Step 1: 停止服务器容器 ==========
                log_to_file("[Step 1/7] 停止服务器容器...")
                stop_cmd = ['ssh', f'{server_user}@{server_host}', 'docker', 'stop', 'ragflowauth-frontend', 'ragflowauth-backend']
                result = subprocess.run(stop_cmd, capture_output=True, text=True)
                # 停止容器失败也算成功（容器可能本来就没运行）
                log_to_file("[Step 1/7] ✓ 容器停止命令已执行")
                self.status_bar.config(text="Step 1/7: ✓ 容器已停止")

                # ========== Step 2: 构建Docker镜像 ==========
                self.status_bar.config(text="Step 2/7: 构建Docker镜像...")
                log_to_file("[Step 2/7] 构建Docker镜像...")

                # 构建后端镜像
                log_to_file("[Step 2/7] 构建后端镜像...")
                build_backend_cmd = f'cd "{repo_root}" && docker build -f backend/Dockerfile -t {backend_image} .'
                result = subprocess.run(build_backend_cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 2/7: ✗ 后端镜像构建失败")
                    log_to_file(f"[Step 2/7] ✗ 后端镜像构建失败: {result.stderr}", "ERROR")
                    return
                log_to_file("[Step 2/7] ✓ 后端镜像构建成功")

                # 构建前端镜像
                log_to_file("[Step 2/7] 构建前端镜像...")
                build_frontend_cmd = f'cd "{repo_root}" && docker build -f fronted/Dockerfile -t {frontend_image} .'
                result = subprocess.run(build_frontend_cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 2/7: ✗ 前端镜像构建失败")
                    log_to_file(f"[Step 2/7] ✗ 前端镜像构建失败: {result.stderr}", "ERROR")
                    return

                self.status_bar.config(text="Step 2/7: ✓ 镜像构建完成")
                log_to_file("[Step 2/7] ✓ 前端镜像构建成功")

                # ========== Step 3: 导出镜像 ==========
                self.status_bar.config(text="Step 3/7: 导出镜像...")
                log_to_file("[Step 3/7] 导出镜像...")

                # 创建临时目录
                temp_dir.mkdir(parents=True, exist_ok=True)

                frontend_tar = temp_dir / f"ragflowauth-frontend-{tag}.tar"
                backend_tar = temp_dir / f"ragflowauth-backend-{tag}.tar"

                # 导出前端镜像
                log_to_file(f"[Step 3/7] 导出前端镜像到 {frontend_tar}...")
                export_frontend_cmd = f"docker save {frontend_image} -o {frontend_tar}"
                result = subprocess.run(export_frontend_cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0 or not frontend_tar.exists():
                    self.status_bar.config(text="Step 3/7: ✗ 前端镜像导出失败")
                    log_to_file(f"[Step 3/7] ✗ 前端镜像导出失败: {result.stderr}", "ERROR")
                    return
                log_to_file(f"[Step 3/7] ✓ 前端镜像导出成功 ({frontend_tar.stat().st_size / 1024 / 1024:.1f} MB)")

                # 导出后端镜像
                log_to_file(f"[Step 3/7] 导出后端镜像到 {backend_tar}...")
                export_backend_cmd = f"docker save {backend_image} -o {backend_tar}"
                result = subprocess.run(export_backend_cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0 or not backend_tar.exists():
                    self.status_bar.config(text="Step 3/7: ✗ 后端镜像导出失败")
                    log_to_file(f"[Step 3/7] ✗ 后端镜像导出失败: {result.stderr}", "ERROR")
                    return

                self.status_bar.config(text="Step 3/7: ✓ 镜像导出完成")
                log_to_file(f"[Step 3/7] ✓ 后端镜像导出成功 ({backend_tar.stat().st_size / 1024 / 1024:.1f} MB)")

                # ========== Step 4: 传输镜像到服务器 ==========
                self.status_bar.config(text="Step 4/7: 传输镜像到服务器...")
                log_to_file("[Step 4/7] 传输镜像到服务器...")

                # 传输前端镜像
                log_to_file(f"[Step 4/7] 传输前端镜像...")
                scp_frontend_cmd = ['scp', str(frontend_tar), f'{server_user}@{server_host}:/tmp/']
                result = subprocess.run(scp_frontend_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 4/7: ✗ 前端镜像传输失败")
                    log_to_file(f"[Step 4/7] ✗ 前端镜像传输失败: {result.stderr}", "ERROR")
                    return
                log_to_file("[Step 4/7] ✓ 前端镜像传输成功")

                # 传输后端镜像
                log_to_file(f"[Step 4/7] 传输后端镜像...")
                scp_backend_cmd = ['scp', str(backend_tar), f'{server_user}@{server_host}:/tmp/']
                result = subprocess.run(scp_backend_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 4/7: ✗ 后端镜像传输失败")
                    log_to_file(f"[Step 4/7] ✗ 后端镜像传输失败: {result.stderr}", "ERROR")
                    return

                self.status_bar.config(text="Step 4/7: ✓ 镜像传输完成")
                log_to_file("[Step 4/7] ✓ 后端镜像传输成功")

                # ========== Step 5: 在服务器上加载镜像 ==========
                self.status_bar.config(text="Step 5/7: 加载镜像到服务器...")
                log_to_file("[Step 5/7] 加载镜像到服务器...")

                frontend_tar_name = frontend_tar.name
                backend_tar_name = backend_tar.name

                # 加载前端镜像
                log_to_file(f"[Step 5/7] 加载前端镜像...")
                load_frontend_cmd = ['ssh', f'{server_user}@{server_host}', 'docker', 'load', '-i', f'/tmp/{frontend_tar_name}']
                result = subprocess.run(load_frontend_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 5/7: ✗ 前端镜像加载失败")
                    log_to_file(f"[Step 5/7] ✗ 前端镜像加载失败: {result.stderr}", "ERROR")
                    return
                log_to_file("[Step 5/7] ✓ 前端镜像加载成功")

                # 加载后端镜像
                log_to_file(f"[Step 5/7] 加载后端镜像...")
                load_backend_cmd = ['ssh', f'{server_user}@{server_host}', 'docker', 'load', '-i', f'/tmp/{backend_tar_name}']
                result = subprocess.run(load_backend_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 5/7: ✗ 后端镜像加载失败")
                    log_to_file(f"[Step 5/7] ✗ 后端镜像加载失败: {result.stderr}", "ERROR")
                    return

                # 清理临时文件
                cleanup_cmd = ['ssh', f'{server_user}@{server_host}', 'rm', '-f', f'/tmp/{frontend_tar_name}', f'/tmp/{backend_tar_name}']
                subprocess.run(cleanup_cmd, capture_output=True)

                self.status_bar.config(text="Step 5/7: ✓ 镜像加载完成")
                log_to_file("[Step 5/7] ✓ 后端镜像加载成功")

                # ========== Step 6: 启动容器 ==========
                self.status_bar.config(text="Step 6/7: 启动容器...")
                log_to_file("[Step 6/7] 启动容器...")

                # 删除旧容器
                log_to_file("[Step 6/7] 删除旧容器...")
                remove_cmd = ['ssh', f'{server_user}@{server_host}', 'docker', 'rm', '-f', 'ragflowauth-frontend', 'ragflowauth-backend']
                subprocess.run(remove_cmd, capture_output=True)

                # 启动前端容器
                log_to_file(f"[Step 6/7] 启动前端容器: {frontend_image}...")
                run_frontend_cmd = [
                    'ssh', f'{server_user}@{server_host}', 'docker', 'run', '-d',
                    '--name', 'ragflowauth-frontend',
                    '--network', network_name,
                    '-p', f'{frontend_port}:80',
                    '--restart', 'unless-stopped',
                    frontend_image
                ]
                result = subprocess.run(run_frontend_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 6/7: ✗ 前端容器启动失败")
                    log_to_file(f"[Step 6/7] ✗ 前端容器启动失败: {result.stderr}", "ERROR")
                    return
                log_to_file("[Step 6/7] ✓ 前端容器启动成功")

                # 启动后端容器
                log_to_file(f"[Step 6/7] 启动后端容器: {backend_image}...")
                run_backend_cmd = [
                    'ssh', f'{server_user}@{server_host}', 'docker', 'run', '-d',
                    '--name', 'ragflowauth-backend',
                    '--network', network_name,
                    '-p', f'{backend_port}:{backend_port}',
                    '-v', f'{data_dir}/data:/app/data',
                    '-v', f'{data_dir}/uploads:/app/uploads',
                    '-v', f'{data_dir}/ragflow_config.json:/app/ragflow_config.json:ro',
                    '-v', f'{data_dir}/ragflow_compose:/app/ragflow_compose:ro',
                    '-v', '/mnt/replica:/mnt/replica',
                    '-v', '/var/run/docker.sock:/var/run/docker.sock:ro',
                    '--restart', 'unless-stopped',
                    backend_image
                ]
                result = subprocess.run(run_backend_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.status_bar.config(text="Step 6/7: ✗ 后端容器启动失败")
                    log_to_file(f"[Step 6/7] ✗ 后端容器启动失败: {result.stderr}", "ERROR")
                    return

                self.status_bar.config(text="Step 6/7: ✓ 容器启动完成")
                log_to_file("[Step 6/7] ✓ 后端容器启动成功")

                # 等待容器启动
                import time
                time.sleep(3)

                # ========== Step 7: 验证部署 ==========
                self.status_bar.config(text="Step 7/7: 验证部署...")
                log_to_file("[Step 7/7] 验证部署...")

                # 检查前端容器状态
                check_frontend_cmd = ['ssh', f'{server_user}@{server_host}', 'docker', 'inspect',
                                     'ragflowauth-frontend', '--format', '{{.State.Status}}']
                result = subprocess.run(check_frontend_cmd, capture_output=True, text=True)
                frontend_status = result.stdout.strip() if result.returncode == 0 else 'not running'

                # 检查后端容器状态
                check_backend_cmd = ['ssh', f'{server_user}@{server_host}', 'docker', 'inspect',
                                    'ragflowauth-backend', '--format', '{{.State.Status}}']
                result = subprocess.run(check_backend_cmd, capture_output=True, text=True)
                backend_status = result.stdout.strip() if result.returncode == 0 else 'not running'

                if frontend_status == "running" and backend_status == "running":
                    self.status_bar.config(text="✓ 部署完成！前端和后端均正常运行")
                    log_to_file("[Step 7/7] ✓ 部署验证成功")
                    log_to_file(f"✓ 前端状态: {frontend_status}")
                    log_to_file(f"✓ 后端状态: {backend_status}")
                    log_to_file(f"✓ 前端URL: http://{server_host}:{frontend_port}")
                    log_to_file(f"✓ 后端URL: http://{server_host}:{backend_port}")
                    log_to_file(f"✓ 镜像标签: {tag}")
                else:
                    self.status_bar.config(text="✗ 部署验证失败")
                    log_to_file(f"[Step 7/7] ✗ 部署验证失败", "ERROR")
                    log_to_file(f"前端状态: {frontend_status}", "ERROR")
                    log_to_file(f"后端状态: {backend_status}", "ERROR")
                    return

                # 清理本地临时文件
                if temp_dir.exists():
                    import shutil
                    shutil.rmtree(temp_dir)
                    log_to_file("✓ 清理本地临时文件")

            except Exception as e:
                self.status_bar.config(text="✗ 部署失败")
                msg = f"[ERROR] 快速部署异常: {str(e)}"
                print(msg)
                log_to_file(msg, "ERROR")

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def smart_quick_restart(self):
        """智能快速重启容器（自动检测镜像标签并修复挂载）"""
        self.status_bar.config(text="正在智能快速重启容器...")

        def execute():
            try:
                if not self.ssh_executor:
                    self.update_ssh_executor()

                # 步骤 1: 检测当前运行的镜像标签
                print("[DEBUG] 步骤 1: 检测当前镜像标签...")
                log_to_file("[QUICK-RESTART] 步骤 1: 检测当前镜像标签")

                # 方法 1: 从 docker images 获取最新的 backend 镜像
                tag_cmd = "docker images --format '{{.Repository}}:{{.Tag}}' | grep 'ragflowauth-backend' | grep -v '<none>' | head -1"
                success, output = self.ssh_executor.execute(tag_cmd)

                # 清理输出中的 SSH 警告信息
                if output:
                    output = '\n'.join(line for line in output.split('\n')
                                       if 'close - IO is still pending' not in line
                                       and 'read:' not in line
                                       and 'write:' not in line
                                       and 'io:' not in line
                                       and line.strip()).strip()

                # 如果方法 1 失败，尝试方法 2: 从运行中的容器获取
                if not success or not output:
                    print("[DEBUG] 方法 1 失败，尝试从运行中的容器获取镜像...")
                    tag_cmd2 = "docker inspect ragflowauth-backend --format '{{.Config.Image}}' 2>/dev/null || echo 'NOT_FOUND'"
                    success, output = self.ssh_executor.execute(tag_cmd2)

                    if output:
                        output = '\n'.join(line for line in output.split('\n')
                                           if 'close - IO is still pending' not in line
                                           and 'read:' not in line
                                           and 'write:' not in line
                                           and 'io:' not in line
                                           and line.strip()).strip()

                    if output and output != 'NOT_FOUND' and 'ragflowauth-backend:' in output:
                        # 输出格式是 "ragflowauth-backend:tag"，提取 tag 部分
                        if ':' in output:
                            current_tag = output.split(':', 1)[1]
                        else:
                            current_tag = output
                    else:
                        # 方法 2 也失败，提供详细诊断信息
                        print("[DEBUG] 获取镜像失败，收集诊断信息...")

                        # 获取所有 ragflowauth 镜像
                        list_cmd = "docker images | grep ragflowauth || echo 'NO_IMAGES'"
                        success, list_output = self.ssh_executor.execute(list_cmd)
                        if list_output:
                            list_output = '\n'.join(line for line in list_output.split('\n')
                                                 if 'close - IO is still pending' not in line
                                                 and 'read:' not in line
                                                 and 'write:' not in line
                                                 and 'io:' not in line
                                                 and line.strip()).strip()

                        # 获取所有运行中的容器
                        ps_cmd = "docker ps || echo 'NO_CONTAINERS'"
                        success, ps_output = self.ssh_executor.execute(ps_cmd)
                        if ps_output:
                            ps_output = '\n'.join(line for line in ps_output.split('\n')
                                               if 'close - IO is still pending' not in line
                                               and 'read:' not in line
                                               and 'write:' not in line
                                               and 'io:' not in line
                                               and line.strip()).strip()

                        error_detail = f"无法检测到 ragflowauth-backend 镜像标签\n\n"
                        error_detail += f"可用镜像:\n{list_output}\n\n"
                        error_detail += f"运行中的容器:\n{ps_output}"

                        raise Exception(error_detail)
                else:
                    # 方法 1 成功，输出格式是 "ragflowauth-backend:tag"，提取 tag 部分
                    if ':' in output:
                        current_tag = output.split(':', 1)[1]
                    else:
                        current_tag = output

                if not current_tag:
                    raise Exception("无法检测到 ragflowauth-backend 镜像标签")

                print(f"[DEBUG] 检测到镜像标签: {current_tag}")
                log_to_file(f"[QUICK-RESTART] 检测到镜像标签: {current_tag}")

                # 步骤 2: 停止后端容器
                print(f"[DEBUG] 步骤 2: 停止后端容器 (tag={current_tag})...")
                log_to_file(f"[QUICK-RESTART] 步骤 2: 停止后端容器")

                stop_cmd = "docker stop ragflowauth-backend 2>/dev/null || echo 'NOT_RUNNING'"
                success, stop_output = self.ssh_executor.execute(stop_cmd)
                print(f"[DEBUG] 停止命令执行完成")

                # 步骤 3: 删除后端容器
                print(f"[DEBUG] 步骤 3: 删除后端容器...")
                log_to_file(f"[QUICK-RESTART] 步骤 3: 删除后端容器")

                rm_cmd = "docker rm ragflowauth-backend 2>/dev/null || echo 'NOT_EXISTS'"
                success, rm_output = self.ssh_executor.execute(rm_cmd)
                print(f"[DEBUG] 删除命令执行完成")

                # 步骤 4: 重新创建后端容器（包含正确的挂载）
                print(f"[DEBUG] 步骤 4: 重新创建后端容器（包含 /mnt/replica 挂载）...")
                log_to_file(f"[QUICK-RESTART] 步骤 4: 重新创建后端容器")

                recreate_cmd = f"""docker run -d \
  --name ragflowauth-backend \
  --network ragflowauth-network \
  -p 8001:8001 \
  -e TZ=Asia/Shanghai \
  -v /opt/ragflowauth/data:/app/data \
  -v /opt/ragflowauth/uploads:/app/uploads \
  -v /opt/ragflowauth/ragflow_config.json:/app/ragflow_config.json:ro \
  -v /opt/ragflowauth/ragflow_compose:/app/ragflow_compose:ro \
  -v /opt/ragflowauth/backup_config.json:/app/backup_config.json:ro \
  -v /mnt/replica:/mnt/replica \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --restart unless-stopped \
  ragflowauth-backend:{current_tag}"""

                success, output = self.ssh_executor.execute(recreate_cmd)

                # 清理输出中的 SSH 警告信息
                if output:
                    output = '\n'.join(line for line in output.split('\n')
                                       if 'close - IO is still pending' not in line
                                       and 'read:' not in line
                                       and 'write:' not in line
                                       and 'io:' not in line
                                       and line.strip()).strip()

                if not success:
                    raise Exception(f"重新创建容器失败:\n{output}")

                # 步骤 5: 等待容器启动并验证状态
                print("[DEBUG] 步骤 5: 等待容器启动并验证状态...")
                log_to_file("[QUICK-RESTART] 步骤 5: 等待容器启动")

                time.sleep(3)  # 等待容器启动

                verify_cmd = "docker ps | grep ragflowauth-backend"
                success, output = self.ssh_executor.execute(verify_cmd)

                # 清理输出中的 SSH 警告信息
                if output:
                    output = '\n'.join(line for line in output.split('\n')
                                       if 'close - IO is still pending' not in line
                                       and 'read:' not in line
                                       and 'write:' not in line
                                       and 'io:' not in line
                                       and line.strip()).strip()

                if not success or not output:
                    raise Exception("容器启动失败：容器未在运行")

                # 步骤 6: 验证 /mnt/replica 挂载
                print("[DEBUG] 步骤 6: 验证 /mnt/replica 挂载...")
                log_to_file("[QUICK-RESTART] 步骤 6: 验证挂载")

                mount_cmd = "docker inspect ragflowauth-backend --format '{{json .Mounts}}' 2>/dev/null | grep -o '/mnt/replica' || echo 'NOT_MOUNTED'"
                success, mount_output = self.ssh_executor.execute(mount_cmd)

                # 清理输出中的 SSH 警告信息
                if mount_output:
                    mount_output = '\n'.join(line for line in mount_output.split('\n')
                                          if 'close - IO is still pending' not in line
                                          and 'read:' not in line
                                          and 'write:' not in line
                                          and 'io:' not in line
                                          and line.strip()).strip()

                mount_ok = success and '/mnt/replica' in mount_output

                # 完成消息
                result_msg = f"✅ 快速重启成功！\n\n"
                result_msg += f"镜像标签: {current_tag}\n"
                result_msg += f"容器状态: 运行中\n"
                result_msg += f"/mnt/replica 挂载: {'✓ 已挂载' if mount_ok else '✗ 未挂载 (需要手动检查)'}\n\n"
                result_msg += f"输出:\n{output}"

                self.status_bar.config(text="快速重启完成")
                print(result_msg)
                log_to_file(f"[QUICK-RESTART] 完成: {current_tag}, 挂载: {'OK' if mount_ok else 'FAIL'}")
                # 不显示弹窗，只更新状态栏和记录日志
                # messagebox.showinfo("快速重启成功", result_msg)

            except Exception as e:
                error_msg = f"快速重启失败：{str(e)}"
                self.status_bar.config(text="快速重启失败")
                print(f"[ERROR] {error_msg}")
                log_to_file(f"[QUICK-RESTART] ERROR: {error_msg}", "ERROR")
                # 不显示弹窗，只更新状态栏和记录日志
                # messagebox.showerror("快速重启失败", error_msg)

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def cleanup_docker_images(self):
        """清理服务器上未使用的 Docker 镜像（仅保留当前运行的镜像）"""
        self.status_bar.config(text="正在清理 Docker 镜像...")

        def execute():
            try:
                if not self.ssh_executor:
                    self.update_ssh_executor()

                # 步骤 1: 获取当前运行的容器使用的镜像
                print("[DEBUG] 步骤 1: 获取当前运行的容器...")
                log_to_file("[CLEANUP-IMAGES] 步骤 1: 获取当前运行的容器")

                ps_cmd = "docker ps --format '{{.Image}}'"
                success, output = self.ssh_executor.execute(ps_cmd)

                # 清理输出中的 SSH 警告信息
                if output:
                    output = '\n'.join(line for line in output.split('\n')
                                       if 'close - IO is still pending' not in line
                                       and 'read:' not in line
                                       and 'write:' not in line
                                       and 'io:' not in line
                                       and line.strip()).strip()

                if not success:
                    raise Exception(f"获取容器列表失败:\n{output}")

                # 提取运行的镜像列表
                running_images = set()
                for line in output.strip().split('\n'):
                    if line:
                        running_images.add(line)

                print(f"[DEBUG] 当前运行的镜像: {running_images}")
                log_to_file(f"[CLEANUP-IMAGES] 运行的镜像: {running_images}")

                # 步骤 2: 获取所有 ragflowauth 镜像
                print("[DEBUG] 步骤 2: 获取所有 ragflowauth 镜像...")
                log_to_file("[CLEANUP-IMAGES] 步骤 2: 获取所有 ragflowauth 镜像")

                images_cmd = "docker images --format '{{.Repository}}:{{.Tag}}' | grep 'ragflowauth' || echo 'NO_IMAGES'"
                success, output = self.ssh_executor.execute(images_cmd)

                if output:
                    output = '\n'.join(line for line in output.split('\n')
                                       if 'close - IO is still pending' not in line
                                       and 'read:' not in line
                                       and 'write:' not in line
                                       and 'io:' not in line
                                       and line.strip()).strip()

                if not success or output == 'NO_IMAGES':
                    raise Exception(f"获取镜像列表失败或没有镜像")

                # 提取所有镜像
                all_images = []
                for line in output.strip().split('\n'):
                    if line and 'ragflowauth' in line:
                        all_images.append(line)

                print(f"[DEBUG] 所有 ragflowauth 镜像: {all_images}")
                log_to_file(f"[CLEANUP-IMAGES] 所有镜像: {all_images}")

                # 步骤 3: 找出未使用的镜像
                unused_images = []
                for image in all_images:
                    if image not in running_images:
                        unused_images.append(image)

                print(f"[DEBUG] 未使用的镜像: {unused_images}")
                log_to_file(f"[CLEANUP-IMAGES] 未使用的镜像: {unused_images}")

                if not unused_images:
                    result_msg = "✅ 没有需要清理的镜像\n\n"
                    result_msg += f"当前运行的镜像数量: {len(running_images)}\n"
                    result_msg += "所有 ragflowauth 镜像都在使用中"

                    self.status_bar.config(text="镜像清理完成")
                    print(result_msg)
                    log_to_file("[CLEANUP-IMAGES] 完成: 没有需要清理的镜像")
                    # 不显示弹窗，只更新状态栏和记录日志
                    # messagebox.showinfo("镜像清理完成", result_msg)
                    return

                # 步骤 4: 删除未使用的镜像
                print(f"[DEBUG] 步骤 4: 删除 {len(unused_images)} 个未使用的镜像...")
                log_to_file(f"[CLEANUP-IMAGES] 步骤 4: 删除未使用的镜像")

                deleted_images = []
                failed_images = []

                for image in unused_images:
                    print(f"[DEBUG] 正在删除: {image}")
                    rmi_cmd = f"docker rmi {image} 2>&1 || echo 'FAILED'"
                    success, output = self.ssh_executor.execute(rmi_cmd)

                    if output:
                        output = '\n'.join(line for line in output.split('\n')
                                           if 'close - IO is still pending' not in line
                                           and 'read:' not in line
                                           and 'write:' not in line
                                           and 'io:' not in line
                                           and line.strip()).strip()

                    if 'FAILED' in output or not success:
                        failed_images.append(image)
                        print(f"[DEBUG] 删除失败: {image}")
                    else:
                        deleted_images.append(image)
                        print(f"[DEBUG] 删除成功: {image}")

                # 步骤 5: 显示清理结果
                print("[DEBUG] 步骤 5: 显示清理结果...")
                log_to_file(f"[CLEANUP-IMAGES] 完成: 删除 {len(deleted_images)} 个, 失败 {len(failed_images)} 个")

                result_msg = f"✅ Docker 镜像清理完成！\n\n"
                result_msg += f"当前运行的镜像: {len(running_images)} 个\n"
                result_msg += f"删除的镜像: {len(deleted_images)} 个\n"
                result_msg += f"失败的镜像: {len(failed_images)} 个\n\n"

                if deleted_images:
                    result_msg += "已删除的镜像:\n"
                    for img in deleted_images:
                        result_msg += f"  ✓ {img}\n"

                if failed_images:
                    result_msg += "\n删除失败的镜像:\n"
                    for img in failed_images:
                        result_msg += f"  ✗ {img}\n"

                # 获取磁盘空间信息
                space_cmd = "docker system df --format 'table {{.Type}}\t{{.TotalCount}}\t{{.Size}}' | head -10"
                success, space_output = self.ssh_executor.execute(space_cmd)

                if success and space_output:
                    space_output = '\n'.join(line for line in space_output.split('\n')
                                          if 'close - IO is still pending' not in line
                                          and 'read:' not in line
                                          and 'write:' not in line
                                          and 'io:' not in line
                                          and line.strip()).strip()
                    result_msg += "\nDocker 空间使用:\n"
                    result_msg += space_output

                self.status_bar.config(text="镜像清理完成")
                print(result_msg)
                log_to_file(f"[CLEANUP-IMAGES] 成功: {deleted_images}, 失败: {failed_images}")
                # 不显示弹窗，只更新状态栏和记录日志
                # messagebox.showinfo("镜像清理完成", result_msg)

            except Exception as e:
                error_msg = f"镜像清理失败：{str(e)}"
                self.status_bar.config(text="镜像清理失败")
                print(f"[ERROR] {error_msg}")
                log_to_file(f"[CLEANUP-IMAGES] ERROR: {error_msg}", "ERROR")
                # 不显示弹窗，只更新状态栏和记录日志
                # messagebox.showerror("镜像清理失败", error_msg)

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
                CYAN = "\033[96m"
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

                # 步骤 5: 验证备份复制功能是否真正工作
                print("[DEBUG] 步骤 5: 验证备份复制功能...")
                log_to_file("[CONTAINER-CHECK] 步骤 5: 验证备份复制功能")

                result_text += "\n" + "=" * 95 + "\n"
                result_text += "备份复制功能验证:\n\n"

                # 5.1 直接从文件系统找到最新备份（不依赖SQL查询）
                print("[DEBUG] 步骤 5.1: 查找最新备份目录...")
                log_to_file("[CONTAINER-CHECK] 步骤 5.1: 查找最新备份目录")

                # 使用ls -t直接找到最新的migration_pack目录
                find_latest_cmd = "ls -td /opt/ragflowauth/data/backups/migration_pack_* 2>/dev/null | head -1"
                success, latest_backup_path = self.ssh_executor.execute(find_latest_cmd)

                if latest_backup_path:
                    latest_backup_path = '\n'.join(line for line in latest_backup_path.split('\n')
                                               if 'close - IO is still pending' not in line
                                               and 'read:' not in line
                                               and 'write:' not in line
                                               and 'io:' not in line).strip()

                backup_name = None
                if latest_backup_path and latest_backup_path != "":
                    backup_name = Path(latest_backup_path).name
                    result_text += f"最新备份目录: {backup_name}\n"
                else:
                    result_text += f"  {RED}✗ 未找到任何备份目录{RESET}\n\n"
                    # 继续执行容器路径检查
                    print("[DEBUG] 未找到备份目录，跳过文件检查")
                    log_to_file("[CONTAINER-CHECK] 未找到备份目录")

                # 5.2 检查主机上的备份文件
                if backup_name:
                    host_backup_path = f"/opt/ragflowauth/data/backups/{backup_name}"

                    # 检查主机上的备份文件
                    host_check_cmd = f"ls -lh {host_backup_path}/ 2>&1 | head -10"
                    success, host_files = self.ssh_executor.execute(host_check_cmd)

                    if host_files:
                        host_files = '\n'.join(line for line in host_files.split('\n')
                                           if 'close - IO is still pending' not in line
                                           and 'read:' not in line
                                           and 'write:' not in line
                                           and 'io:' not in line).strip()

                    result_text += "主机备份文件:\n"
                    has_auth_db = "auth.db" in host_files if host_files else False
                    has_volumes = "volumes" in host_files if host_files else False

                    if has_auth_db:
                        result_text += f"  {GREEN}✓ auth.db 存在{RESET}\n"
                    else:
                        result_text += f"  {RED}✗ auth.db 缺失{RESET}\n"

                    if has_volumes:
                        result_text += f"  {GREEN}✓ volumes 目录存在{RESET}\n"
                        # 检查volumes目录内容
                        volumes_check_cmd = f"ls {host_backup_path}/volumes/ 2>&1 | wc -l"
                        success, volumes_count = self.ssh_executor.execute(volumes_check_cmd)
                        if volumes_count:
                            volumes_count = volumes_count.strip()
                            result_text += f"    volumes 文件数: {volumes_count}\n"
                    else:
                        result_text += f"  {RED}✗ volumes 目录缺失{RESET}\n"

                    result_text += "\n"

                    # 5.3 检查Windows共享上的备份文件
                    replica_backup_path = f"/mnt/replica/RagflowAuth/{backup_name}"
                    replica_check_cmd = f"ls -lh {replica_backup_path}/ 2>&1 | head -10"
                    success, replica_files = self.ssh_executor.execute(replica_check_cmd)

                    if replica_files:
                        replica_files = '\n'.join(line for line in replica_files.split('\n')
                                              if 'close - IO is still pending' not in line
                                              and 'read:' not in line
                                              and 'write:' not in line
                                              and 'io:' not in line).strip()

                    result_text += "Windows共享备份文件:\n"
                    replica_has_auth_db = "auth.db" in replica_files if replica_files else False
                    replica_has_volumes = "volumes" in replica_files if replica_files else False

                    if replica_has_auth_db:
                        result_text += f"  {GREEN}✓ auth.db 存在{RESET}\n"
                    else:
                        result_text += f"  {RED}✗ auth.db 缺失{RESET}\n"

                    if replica_has_volumes:
                        result_text += f"  {GREEN}✓ volumes 目录存在{RESET}\n"
                        # 检查volumes目录内容
                        replica_volumes_check = f"ls {replica_backup_path}/volumes/ 2>&1 | wc -l"
                        success, replica_volumes_count = self.ssh_executor.execute(replica_volumes_check)
                        if replica_volumes_count:
                            replica_volumes_count = replica_volumes_count.strip()
                            result_text += f"    volumes 文件数: {replica_volumes_count}\n"
                    else:
                        result_text += f"  {RED}✗ volumes 目录缺失{RESET}\n"
                        result_text += f"    {RED}⚠️  警告: 备份复制功能未正常工作！{RESET}\n"

                    result_text += "\n"

                    # 5.4 对比主机和Windows共享
                    result_text += "复制状态对比:\n"
                    if has_volumes and replica_has_volumes:
                        result_text += f"  {GREEN}✓ volumes 目录已成功复制{RESET}\n"
                    elif has_volumes and not replica_has_volumes:
                        result_text += f"  {RED}✗ volumes 目录未复制到Windows共享{RESET}\n"
                        result_text += f"    {RED}问题: 路径转换错误或复制功能失败{RESET}\n"
                    elif not has_volumes:
                        result_text += f"  {RED}✗ 主机备份本身就缺少volumes目录{RESET}\n"

                    if has_auth_db and replica_has_auth_db:
                        result_text += f"  {GREEN}✓ auth.db 已成功复制{RESET}\n"
                    elif has_auth_db and not replica_has_auth_db:
                        result_text += f"  {RED}✗ auth.db 未复制到Windows共享{RESET}\n"

                    # 5.5 查询数据库中的备份状态（补充信息）
                    result_text += "\n数据库备份记录:\n"
                    db_query_cmd = f"""docker exec ragflowauth-backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/auth.db')
cur = conn.cursor()
cur.execute('SELECT id, kind, status, message FROM backup_jobs WHERE output_dir LIKE \\\"%{backup_name}%\\\" ORDER BY id DESC LIMIT 1')
row = cur.fetchone()
if row:
    print(f'ID:{{row[0]}}|TYPE:{{row[1]}}|STATUS:{{row[2]}}|MSG:{{row[3]}}')
else:
    print('NOT_FOUND')
conn.close()
"
"""
                    success, db_info = self.ssh_executor.execute(db_query_cmd)

                    if db_info:
                        db_info = '\n'.join(line for line in db_info.split('\n')
                                          if 'close - IO is still pending' not in line
                                          and 'read:' not in line
                                          and 'write:' not in line
                                          and 'io:' not in line).strip()

                    if db_info and "ID:" in db_info:
                        # 解析数据库信息
                        for line in db_info.split('\n'):
                            if line.startswith("ID:"):
                                parts = line.split('|')
                                db_id = parts[0].split(':')[1].strip() if len(parts) > 0 else "?"
                                db_type = parts[1].split(':')[1].strip() if len(parts) > 1 else "?"
                                db_status = parts[2].split(':')[1].strip() if len(parts) > 2 else "?"
                                db_msg = parts[3].split(':', 1)[1].strip() if len(parts) > 3 else ""

                                result_text += f"  备份ID: {db_id}\n"
                                result_text += f"  备份类型: {db_type}\n"
                                result_text += f"  数据库状态: {db_status}\n"
                                result_text += f"  消息: {db_msg}\n"
                                break
                    else:
                        result_text += f"  ⚠️  未找到数据库记录\n"

                # 5.6 检查容器内的备份路径访问
                result_text += "\n容器内备份路径验证:\n"
                container_path_check = "docker exec ragflowauth-backend python -c \"from pathlib import Path; p = Path('/app/data/backups'); print(f'EXISTS:{p.exists()}'); print(f'COUNT:{len(list(p.iterdir())) if p.exists() else 0}')\""
                success, container_path_info = self.ssh_executor.execute(container_path_check)

                if container_path_info:
                    container_path_info = '\n'.join(line for line in container_path_info.split('\n')
                                                 if 'close - IO is still pending' not in line
                                                 and 'read:' not in line
                                                 and 'write:' not in line
                                                 and 'io:' not in line).strip()

                    if "EXISTS:True" in container_path_info:
                        result_text += f"  {GREEN}✓ 容器可以访问 /app/data/backups{RESET}\n"
                        for line in container_path_info.split('\n'):
                            if "COUNT:" in line:
                                count = line.split(":")[1]
                                result_text += f"    可见备份数量: {count}\n"
                    else:
                        result_text += f"  {RED}✗ 容器无法访问 /app/data/backups{RESET}\n"

                # 步骤 7.5: 添加操作建议
                print("[DEBUG] 步骤 7.5: 生成操作建议...")
                log_to_file("[CONTAINER-CHECK] 步骤 7.5: 生成操作建议")

                # 检查是否有错误需要修复
                if backup_name:
                    # 检查volumes文件数
                    if "volumes 文件数: 0" in result_text:
                        result_text += "\n" + "=" * 95 + "\n"
                        result_text += "🔧 操作建议:\n\n"
                        result_text += "问题: 主机备份的volumes目录为空\n\n"
                        result_text += "可能原因:\n"
                        result_text += "  1. Docker volumes备份功能未正常运行\n"
                        result_text += "  2. 容器内无法访问Docker socket\n\n"

                        result_text += "解决方案:\n"
                        result_text += f"  {CYAN}方案1: 检查备份配置{RESET}\n"
                        result_text += "  操作: 在「数据安全」页面检查「备份类型」是否设置为「全量备份」\n"
                        result_text += "  位置: tool.py → 数据安全 → 立即执行备份 → 选择「全量备份」\n\n"

                        result_text += f"  {CYAN}方案2: 手动触发全量备份{RESET}\n"
                        result_text += "  操作: 在「数据安全」页面点击「立即执行全量备份」\n"
                        result_text += "  验证: 备份完成后，检查 /opt/ragflowauth/data/backups/ 目录下最新备份的volumes子目录\n\n"

                        result_text += f"  {CYAN}方案3: 检查Docker socket权限{RESET}\n"
                        result_text += "  命令: docker exec ragflowauth-backend ls -la /var/run/docker.sock\n"
                        result_text += "  预期: 应该显示docker.sock文件存在\n\n"

                    # 检查Windows共享volumes缺失
                    if "volumes 目录缺失" in result_text or "volumes 文件数: 0" in result_text and "Windows共享" in result_text:
                        if "🔧 操作建议:" not in result_text:
                            result_text += "\n" + "=" * 95 + "\n"
                            result_text += "🔧 操作建议:\n\n"
                            result_text += "问题: volumes目录未复制到Windows共享或为空\n\n"

                        result_text += f"  {CYAN}方案1: 使用tool.py快速部署（推荐）{RESET}\n"
                        result_text += "  步骤:\n"
                        result_text += "    1. 点击tool.py左侧的「快速部署」按钮\n"
                        result_text += "    2. 等待镜像构建完成（约2-3分钟）\n"
                        result_text += "    3. 等待镜像传输完成（约1-2分钟，取决于网络）\n"
                        result_text += "    4. 等待容器启动完成\n\n"

                        result_text += f"  {CYAN}方案2: 手动部署修复代码{RESET}\n"
                        result_text += "  步骤:\n"
                        result_text += "    1. 本地重新构建镜像:\n"
                        result_text += "       cd D:\\ProjectPackage\\RagflowAuth\\docker\n"
                        result_text += "       docker compose build --no-cache backend\n\n"
                        result_text += "    2. 导出镜像:\n"
                        result_text += "       docker save ragflowauth-backend:local -o ragflowauth-backend.tar\n\n"
                        result_text += "    3. 传输到服务器:\n"
                        result_text += "       scp ragflowauth-backend.tar root@172.30.30.57:/tmp/\n\n"
                        result_text += "    4. 在服务器上加载并重启:\n"
                        result_text += "       ssh root@172.30.30.57\n"
                        result_text += "       docker load -i /tmp/ragflowauth-backend.tar\n"
                        result_text += "       docker stop ragflowauth-backend\n"
                        result_text += "       docker rm ragflowauth-backend\n"
                        result_text += "       docker run -d --name ragflowauth-backend --network ragflowauth-network \\\n"
                        result_text += "         -p 8001:8001 -v /opt/ragflowauth/data:/app/data \\\n"
                        result_text += "         -v /opt/ragflowauth/uploads:/app/uploads \\\n"
                        result_text += "         -v /mnt/replica:/mnt/replica \\\n"
                        result_text += "         -v /var/run/docker.sock:/var/run/docker.sock:ro \\\n"
                        result_text += "         --restart unless-stopped ragflowauth-backend:local\n\n"

                        result_text += f"  {CYAN}方案3: 使用快速重启（仅修复挂载）{RESET}\n"
                        result_text += "  步骤:\n"
                        result_text += "    1. 点击tool.py左侧的「快速重启容器」按钮\n"
                        result_text += "    2. 等待容器重启完成\n\n"

                        result_text += "验证步骤:\n"
                        result_text += "  1. 在「数据安全」页面点击「立即执行增量备份」\n"
                        result_text += "  2. 等待备份完成\n"
                        result_text += "  3. 点击tool.py的「查看运行中的容器」按钮\n"
                        result_text += "  4. 检查「Windows共享文件检查」部分，volumes目录应该存在且有文件\n\n"

                    # 检查/mnt/replica挂载缺失
                    if "/mnt/replica 挂载缺失" in result_text:
                        if "🔧 操作建议:" not in result_text:
                            result_text += "\n" + "=" * 95 + "\n"
                            result_text += "🔧 操作建议:\n\n"
                            result_text += "问题: 后端容器缺少 /mnt/replica 挂载\n\n"
                        else:
                            result_text += "\n附加问题: 后端容器缺少 /mnt/replica 挂载\n\n"

                        result_text += f"  {CYAN}解决方案: 快速重启容器{RESET}\n"
                        result_text += "  操作: 点击tool.py左侧的「快速重启容器」按钮\n"
                        result_text += "  说明: 该按钮会自动检测当前镜像标签，并使用正确的挂载配置重新创建容器\n\n"

                print("[DEBUG] 步骤 8: 生成结果...")
                log_to_file("[CONTAINER-CHECK] 步骤 8: 生成结果")

                result_text += "\n" + "=" * 95 + "\n"
                result_text += f"说明: {GREEN}✓ = 符合预期{RESET}, {RED}✗ = 需要修复{RESET}, ⚠️  = 警告\n"

                # 不显示结果窗口，只记录到日志和控制台
                print("[DEBUG] 容器检查完成...")
                log_to_file(f"[CONTAINER-CHECK] 显示结果窗口")
                print(result_text)
                # 不显示弹窗，只更新状态栏和记录日志
                # self.show_result_window("容器列表及挂载状态", result_text)
                self.status_bar.config(text="容器信息获取完成")
                log_to_file("[CONTAINER-CHECK] 完成")

            except Exception as e:
                error_msg = f"获取容器信息失败：{str(e)}"
                print(f"[ERROR] {error_msg}")
                log_to_file(f"[CONTAINER-CHECK] ERROR: {error_msg}", "ERROR")
                import traceback
                traceback.print_exc()
                # 不显示弹窗，只更新状态栏和记录日志
                # messagebox.showerror("错误", error_msg)
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
        url = f"https://{self.config.ip}:9002"
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
