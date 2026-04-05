from ._shared import _tool_mod, _delegate

def copy_release_history_to_clipboard(app, *args, **kwargs):
    return _delegate(app, "_copy_release_history_to_clipboard_impl", "copy_release_history_to_clipboard", *args, **kwargs)

def copy_release_history_to_clipboard_impl(app):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file

    try:
        text = ""
        if hasattr(self, "release_history_text"):
            text = self.release_history_text.get("1.0", tk.END)
        if not text.strip():
            messagebox.showwarning("提示", "暂无可复制的发布记录")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        if hasattr(self, "status_bar"):
            self.status_bar.config(text="发布记录已复制到剪贴板")
    except Exception as e:
        log_to_file(f"[ReleaseHistory] copy failed: {e}", "ERROR")
        messagebox.showerror("错误", f"复制失败：{e}")
