from ._shared import _tool_mod


def open_frontend_impl(app):
    tool_mod = _tool_mod()
    self = app
    webbrowser = tool_mod.webbrowser

    self.update_ssh_executor()
    url = f"http://{self.config.ip}:3001"
    self.status_bar.config(text=f"Opening frontend: {url}")
    webbrowser.open(url)


def open_portainer_impl(app):
    tool_mod = _tool_mod()
    self = app
    webbrowser = tool_mod.webbrowser

    self.update_ssh_executor()
    url = f"https://{self.config.ip}:9002"
    self.status_bar.config(text=f"Opening Portainer: {url}")
    webbrowser.open(url)


def open_web_console_impl(app):
    tool_mod = _tool_mod()
    self = app
    webbrowser = tool_mod.webbrowser

    self.update_ssh_executor()
    url = f"https://{self.config.ip}:9090/"
    self.status_bar.config(text=f"Opening web console: {url}")
    webbrowser.open(url)


def open_custom_url_impl(app):
    tool_mod = _tool_mod()
    self = app
    messagebox = tool_mod.messagebox
    log_to_file = tool_mod.log_to_file
    webbrowser = tool_mod.webbrowser

    url = self.url_var.get()
    if url and url != "http://":
        self.status_bar.config(text=f"Opening: {url}")
        log_to_file(f"[URL] Open custom URL: {url}")
        webbrowser.open(url)
    else:
        msg = "[WARNING] Please input a valid URL"
        print(msg)
        log_to_file(msg, "WARNING")
        messagebox.showwarning("Warning", "Please input a valid URL")

