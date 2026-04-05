from ._shared import _tool_mod


def on_environment_changed_impl(app, event=None):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file

    _ = event
    env_name = self.env_var.get()

    if self.config.set_environment(env_name):
        self.ip_var.set(self.config.ip)
        self.user_var.set(self.config.user)
        self.status_bar.config(text=f"Switched to: {env_name} (editable)")
        msg = f"[INFO] Environment switched: {env_name} ({self.config.user}@{self.config.ip})"
        print(msg)
        log_to_file(msg)

        if hasattr(self, "web_desc_label"):
            self.web_desc_label.config(
                text=(
                    "Web 管理界面 - RagflowAuth 后台管理\n"
                    f"访问 https://{self.config.ip}:9090/ 进行后台管理"
                )
            )
        self.refresh_admin_tabs()
    else:
        messagebox.showerror("Error", f"Unknown environment: {env_name}")


def init_field_states_impl(app):
    self = app
    self.ip_entry.config(state="normal")
    self.user_entry.config(state="normal")


def save_config_impl(app):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file

    self.config.ip = self.ip_var.get()
    self.config.user = self.user_var.get()
    self.config.environment = self.env_var.get()
    self.config.save_config()
    self.refresh_admin_tabs()
    self.status_bar.config(text="Configuration saved")
    msg = f"[INFO] Config saved: {self.config.environment} ({self.config.user}@{self.config.ip})"
    print(msg)
    log_to_file(msg)
    messagebox.showinfo(
        "Success",
        (
            "Configuration saved\n\n"
            f"Environment: {self.config.environment}\n"
            f"Server: {self.config.user}@{self.config.ip}"
        ),
    )

