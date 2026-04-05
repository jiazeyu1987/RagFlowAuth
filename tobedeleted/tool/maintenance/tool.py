#!/usr/bin/env python3
"""
RagflowAuth 服务器管理工具
功能：
1. 通过 SSH 执行服务器端工具脚本
2. 快速导航到 Web 管理界面
3. 管理 Docker 容器和镜像
"""

import sys
from pathlib import Path

# Allow importing `tool.*` modules when this file is executed directly.
if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tool.maintenance.tool_runtime_exports import *  # compatibility re-exports for controllers
from tool.maintenance.controllers.tool_delegate_mixin import RagflowAuthToolDelegateMixin

# 日志配置已迁移到 tool.maintenance.core.logging_setup
# 环境配置/固定常量已迁移到 tool.maintenance.core.*
class RagflowAuthTool(RagflowAuthToolDelegateMixin):
    """RagflowAuth 服务器管理工具主窗口"""

    def __init__(self, root):
        self.root = root
        self.root.title("RagflowAuth Maintenance Tool")
        self.root.geometry("900x700")

        self.config = ServerConfig()
        self.ssh_executor = None

        # 记录初始化
        log_to_file(f"UI 初始化完成，默认服务器: {self.config.user}@{self.config.ip}")

        self.setup_ui()

        # 根据当前环境初始化字段状态
        self._init_field_states()

    def show_text_window(self, title: str, content: str):
        from tool.maintenance.controllers.ui_window_controller import show_text_window_impl

        return show_text_window_impl(self, title, content)

    def _insert_colored_text(self, text_widget, content: str):
        from tool.maintenance.controllers.ui_window_controller import insert_colored_text_impl

        return insert_colored_text_impl(self, text_widget, content)

    def _copy_to_clipboard(self, content: str):
        from tool.maintenance.controllers.ui_window_controller import copy_to_clipboard_impl

        return copy_to_clipboard_impl(self, content)

    def setup_ui(self):
        from tool.maintenance.controllers.ui_setup_controller import setup_ui_impl

        return setup_ui_impl(self)

    def create_tools_tab(self):
        """工具页签 UI（拆分到独立模块）。"""
        from tool.maintenance.ui.tools_tab import build_tools_tab

        build_tools_tab(self)

    def create_web_links_tab(self):
        """Web 管理页签 UI（拆分到独立模块）。"""
        from tool.maintenance.ui.web_links_tab import build_web_links_tab

        build_web_links_tab(self)

    def create_restore_tab(self):
        """数据还原页签 UI（拆分到独立模块；还原只允许测试服务器）。"""
        from tool.maintenance.ui.restore_tab import build_restore_tab

        build_restore_tab(self)

    def refresh_local_restore_list(self):
        from tool.maintenance.controllers.restore_controller import refresh_local_restore_list_impl as controller_refresh_local_restore_list_impl

        return controller_refresh_local_restore_list_impl(self)

    def on_restore_backup_selected(self, _event=None):
        from tool.maintenance.controllers.restore_controller import on_restore_backup_selected_impl as controller_on_restore_backup_selected_impl

        return controller_on_restore_backup_selected_impl(self, _event=_event)

    def create_release_tab(self):
        """发布页签 UI（拆分到独立模块，回调仍在 tool.py 中）。"""
        from tool.maintenance.ui.release_tab import build_release_tab

        build_release_tab(self)

    def create_onlyoffice_tab(self):
        """ONLYOFFICE 发布页签 UI（按钮回调在 tool.py 中）。"""
        from tool.maintenance.ui.onlyoffice_tab import build_onlyoffice_tab

        build_onlyoffice_tab(self)

    def create_smoke_tab(self):
        """冒烟测试页签 UI（拆分到独立模块）。"""
        from tool.maintenance.ui.smoke_tab import build_smoke_tab

        build_smoke_tab(self)


def main():
    """主函数"""
    # 记录应用启动
    log_to_file("=" * 80)
    log_to_file("RagflowAuth 工具启动")
    log_to_file(f"日志文件: {LOG_FILE}")
    log_to_file("=" * 80)

    try:
        root = tk.Tk()
        # Start maximized/fullscreen when possible.
        try:
            root.state("zoomed")
        except Exception:
            try:
                root.attributes("-fullscreen", True)
            except Exception:
                pass
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
