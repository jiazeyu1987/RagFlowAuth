from ._shared import _tool_mod


def show_text_window_impl(app, title: str, content: str):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    ttk = tool_mod.ttk
    scrolledtext = tool_mod.scrolledtext

    window = tk.Toplevel(self.root)
    window.title(title)
    window.geometry("800x600")

    text_widget = scrolledtext.ScrolledText(window, wrap=tk.WORD, font=("Courier New", 10), padx=10, pady=10)
    text_widget.pack(fill=tk.BOTH, expand=True)
    text_widget.tag_config("red", foreground="red")
    text_widget.tag_config("green", foreground="green")

    self._insert_colored_text(text_widget, content)
    text_widget.config(state=tk.DISABLED)

    button_frame = ttk.Frame(window)
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

    ttk.Button(button_frame, text="Copy All", command=lambda: self._copy_to_clipboard(content)).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Close", command=window.destroy).pack(side=tk.RIGHT, padx=5)


def insert_colored_text_impl(app, text_widget, content: str):
    tool_mod = _tool_mod()
    tk = tool_mod.tk

    import re

    pattern = r"\[(RED|GREEN)\](.*?)\[/\1\]"
    pos = 0
    for match in re.finditer(pattern, content, re.DOTALL):
        if match.start() > pos:
            text_widget.insert(tk.END, content[pos : match.start()])
        color = match.group(1).lower()
        colored_text = match.group(2)
        text_widget.insert(tk.END, colored_text, color)
        pos = match.end()
    if pos < len(content):
        text_widget.insert(tk.END, content[pos:])


def copy_to_clipboard_impl(app, content: str):
    self = app

    import re

    clean_content = re.sub(r"\[(RED|GREEN)\](.*?)\[/\1\]", r"\2", content, flags=re.DOTALL)
    self.root.clipboard_clear()
    self.root.clipboard_append(clean_content)
    self.status_bar.config(text="Copied to clipboard")

