from ._shared import _tool_mod


def test_connection_impl(app):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file

    self.update_ssh_executor()
    success, output = self.ssh_executor.execute("echo 'Connection successful'")
    if success and "Connection successful" in output:
        self.status_bar.config(text="Connection test succeeded")
        msg = f"[INFO] Connected to {self.config.user}@{self.config.ip}"
        print(msg)
        log_to_file(msg)
        messagebox.showinfo("Success", f"Connected to {self.config.user}@{self.config.ip}")
    else:
        self.status_bar.config(text="Connection test failed")
        msg = f"[ERROR] Failed to connect to {self.config.user}@{self.config.ip}\nError: {output}"
        print(msg)
        log_to_file(msg, "ERROR")
        messagebox.showerror("Failed", f"Failed to connect to {self.config.user}@{self.config.ip}\n\nError: {output}")


def update_ssh_executor_impl(app):
    tool_mod = _tool_mod()
    self = app
    SSHExecutor = tool_mod.SSHExecutor

    self.config.ip = self.ip_var.get().strip()
    self.config.user = self.user_var.get().strip()

    if not self.config.ip:
        print("[ERROR] Server IP is missing")
        return False

    if not self.config.user:
        print("[ERROR] Server user is missing")
        return False

    self.ssh_executor = SSHExecutor(self.config.ip, self.config.user)
    return True

