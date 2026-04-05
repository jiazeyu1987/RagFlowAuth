from ._shared import _tool_mod


def show_backup_file_details_impl(app, side):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    scrolledtext = tool_mod.scrolledtext
    messagebox = tool_mod.messagebox

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

def delete_complete_impl(app, deleted, failed):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    scrolledtext = tool_mod.scrolledtext
    messagebox = tool_mod.messagebox

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
