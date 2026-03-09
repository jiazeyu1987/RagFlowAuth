#!/usr/bin/env python3
"""
RagflowAuth 鏈嶅姟鍣ㄧ鐞嗗伐鍏?
鍔熻兘锛?1. 閫氳繃 SSH 鎵ц鏈嶅姟鍣ㄧ宸ュ叿鑴氭湰
2. 蹇€熷鑸埌 Web 绠＄悊鐣岄潰
3. 绠＄悊 Docker 瀹瑰櫒鍜岄暅鍍?"""

import sys
from pathlib import Path

# Allow importing `tool.*` modules when this file is executed directly.
if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tool.maintenance.tool_runtime_exports import *  # compatibility re-exports for controllers
from tool.maintenance.controllers.tool_delegate_mixin import RagflowAuthToolDelegateMixin

# 锛堟棩蹇楅厤缃凡杩佺Щ鍒?tool.maintenance.core.logging_setup锛?# 锛堥厤缃?鐜/鍥哄畾鍏变韩甯搁噺宸茶縼绉诲埌 tool.maintenance.core.*锛?
class RagflowAuthTool(RagflowAuthToolDelegateMixin):
    """RagflowAuth 鏈嶅姟鍣ㄧ鐞嗗伐鍏蜂富绐楀彛"""

    def __init__(self, root):
        self.root = root
        self.root.title("RagflowAuth Maintenance Tool")
        self.root.geometry("900x700")

        self.config = ServerConfig()
        self.ssh_executor = None

        # 璁板綍鍒濆鍖?        log_to_file(f"UI 鍒濆鍖栧畬鎴愶紝榛樿鏈嶅姟鍣? {self.config.user}@{self.config.ip}")

        self.setup_ui()

        # 鏍规嵁褰撳墠鐜鍒濆鍖栧瓧娈电姸鎬?        self._init_field_states()

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
        """宸ュ叿椤电 UI锛堟媶鍒嗗埌鐙珛妯″潡锛夈€?"""
        from tool.maintenance.ui.tools_tab import build_tools_tab

        build_tools_tab(self)

    def create_web_links_tab(self):
        """Web 绠＄悊椤电 UI锛堟媶鍒嗗埌鐙珛妯″潡锛夈€?"""
        from tool.maintenance.ui.web_links_tab import build_web_links_tab

        build_web_links_tab(self)

    def create_restore_tab(self):
        """鏁版嵁杩樺師椤电 UI锛堟媶鍒嗗埌鐙珛妯″潡锛涜繕鍘熷彧鍏佽娴嬭瘯鏈嶅姟鍣級銆?"""
        from tool.maintenance.ui.restore_tab import build_restore_tab

        build_restore_tab(self)

    def refresh_local_restore_list(self):
        from tool.maintenance.controllers.restore_controller import refresh_local_restore_list_impl as controller_refresh_local_restore_list_impl

        return controller_refresh_local_restore_list_impl(self)

    def on_restore_backup_selected(self, _event=None):
        from tool.maintenance.controllers.restore_controller import on_restore_backup_selected_impl as controller_on_restore_backup_selected_impl

        return controller_on_restore_backup_selected_impl(self, _event=_event)

    def create_release_tab(self):
        """鍙戝竷锛氬彂甯冮〉绛?UI锛堟媶鍒嗗埌鐙珛妯″潡锛屽洖璋冧粛鍦?tool.py 閲岋級銆?"""
        from tool.maintenance.ui.release_tab import build_release_tab

        build_release_tab(self)

    def create_onlyoffice_tab(self):
        """ONLYOFFICE 鍙戝竷椤电 UI锛堟寜閽洖璋冨湪 tool.py 閲岋級銆?"""
        from tool.maintenance.ui.onlyoffice_tab import build_onlyoffice_tab

        build_onlyoffice_tab(self)

    def create_smoke_tab(self):
        """鍐掔儫娴嬭瘯椤电 UI锛堟媶鍒嗗埌鐙珛妯″潡锛夈€?"""
        from tool.maintenance.ui.smoke_tab import build_smoke_tab

        build_smoke_tab(self)


def main():
    """涓诲嚱鏁?"""
    # 璁板綍搴旂敤鍚姩
    log_to_file("=" * 80)
    log_to_file(f"RagflowAuth 宸ュ叿鍚姩")
    log_to_file(f"鏃ュ織鏂囦欢: {LOG_FILE}")
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
        error_msg = f"鏈崟鑾风殑寮傚父: {str(e)}"
        print(error_msg)
        log_to_file(error_msg, "ERROR")
        import traceback
        log_to_file(traceback.format_exc(), "ERROR")
        raise


if __name__ == "__main__":
    main()






