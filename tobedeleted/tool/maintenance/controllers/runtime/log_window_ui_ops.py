import queue


def build_log_window_ui(self, *, command, tk, ttk, scrolledtext):
    log_window = tk.Toplevel(self.root)
    log_window.title(f"Log Viewer: {command}")
    log_window.geometry("800x600")

    output_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD, font=("Consolas", 10))
    output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    btn_frame = ttk.Frame(log_window)
    btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

    stop_state = {"stopped": False}
    process_holder = {"p": None}
    queue_obj: "queue.Queue[str | None]" = queue.Queue()

    def append_fn(text: str) -> None:
        output_text.insert(tk.END, text)
        output_text.see(tk.END)

    def stop_process() -> None:
        stop_state["stopped"] = True
        proc = process_holder.get("p")
        try:
            if proc and proc.poll() is None:
                proc.terminate()
        except Exception:
            pass

    def on_close() -> None:
        stop_process()
        log_window.destroy()

    ttk.Button(btn_frame, text="Stop", command=stop_process).pack(side=tk.LEFT)
    ttk.Button(btn_frame, text="Close", command=on_close).pack(side=tk.LEFT, padx=(8, 0))
    log_window.protocol("WM_DELETE_WINDOW", on_close)

    return {
        "window": log_window,
        "append": append_fn,
        "stop_state": stop_state,
        "process_holder": process_holder,
        "queue": queue_obj,
    }
