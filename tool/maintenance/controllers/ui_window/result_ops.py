from ._shared import _tool_mod


def show_result_window_impl(app, title, content):
    tool_mod = _tool_mod()
    self = app
    tk = tool_mod.tk
    ttk = tool_mod.ttk

    result_window = tk.Toplevel(self.root)
    result_window.title(title)
    result_window.geometry("800x600")

    text_frame = ttk.Frame(result_window)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
    text_widget.pack(fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(text_widget, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget.tag_config("green", foreground="green")
    text_widget.tag_config("red", foreground="red")

    import re

    ansi_escape = re.compile(r"\033\[(\d+(;\d+)*)?m")
    lines = content.split("\n")
    for line in lines:
        last_pos = 0
        current_tag = None

        for match in ansi_escape.finditer(line):
            if match.start() > last_pos:
                normal_text = line[last_pos : match.start()]
                if current_tag:
                    text_widget.insert(tk.END, normal_text, current_tag)
                else:
                    text_widget.insert(tk.END, normal_text)

            code = match.group()
            if "\033[92m" in code:
                current_tag = "green"
            elif "\033[91m" in code:
                current_tag = "red"
            elif "\033[0m" in code:
                current_tag = None

            last_pos = match.end()

        if last_pos < len(line):
            remaining_text = line[last_pos:]
            if current_tag:
                text_widget.insert(tk.END, remaining_text, current_tag)
            else:
                text_widget.insert(tk.END, remaining_text)

        text_widget.insert(tk.END, "\n")

    text_widget.config(state=tk.DISABLED)
    close_button = ttk.Button(result_window, text="Close", command=result_window.destroy)
    close_button.pack(pady=10)

