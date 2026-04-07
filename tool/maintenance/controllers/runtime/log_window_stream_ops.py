def build_tail_log_worker(self, *, command, subprocess_mod, queue_obj, stop_state, process_holder):
    def tail_log_worker():
        try:
            user = self.ssh_executor.user
            host = self.ssh_executor.ip
            ssh_argv = [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "-o",
                "ControlMaster=no",
                f"{user}@{host}",
                command,
            ]
            proc = subprocess_mod.Popen(
                ssh_argv,
                stdout=subprocess_mod.PIPE,
                stderr=subprocess_mod.STDOUT,
                stdin=subprocess_mod.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            process_holder["p"] = proc
            if not proc.stdout:
                queue_obj.put("[ERROR] stdout is not available\n")
                return
            for line in proc.stdout:
                if stop_state["stopped"]:
                    break
                queue_obj.put(line)
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        except Exception as exc:
            queue_obj.put(f"\n[ERROR] {exc}\n")
        finally:
            queue_obj.put(None)

    return tail_log_worker


def build_window_queue_poller(*, queue_obj, append_fn, stop_state, log_window):
    def poll_queue():
        try:
            while True:
                item = queue_obj.get_nowait()
                if item is None:
                    append_fn("\n[INFO] Stopped.\n")
                    return
                append_fn(item)
        except Exception:
            pass

        if not stop_state["stopped"] and log_window.winfo_exists():
            log_window.after(80, poll_queue)

    return poll_queue
