from ._shared import _tool_mod


def get_backup_files_impl(app, directory):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    scrolledtext = tool_mod.scrolledtext
    messagebox = tool_mod.messagebox

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

def update_file_trees_impl(app, left_files, right_files):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    scrolledtext = tool_mod.scrolledtext
    messagebox = tool_mod.messagebox

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

def get_file_size_impl(app, path):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    scrolledtext = tool_mod.scrolledtext
    messagebox = tool_mod.messagebox

    """获取文件或目录大小"""
    # 获取目录大小
    cmd = f"du -sh {path} 2>/dev/null | cut -f1"
    success, output = self.ssh_executor.execute(cmd)
    if success and output.strip():
        return output.strip().split('\n')[0]
    return "N/A"
