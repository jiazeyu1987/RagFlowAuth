def get_mount_diagnostic_info_impl(app):
    self = app
    """Collect mount diagnostics summary."""
    try:
        diag_lines = []
        win_host = (self.config.windows_share_host or "").strip()

        success, output = self.ssh_executor.execute("mount | grep /mnt/replica")
        if success and output.strip():
            diag_lines.append(f"Current mount status:\n{output}\n")
        else:
            diag_lines.append("Current mount status: /mnt/replica is not mounted\n")

        success, output = self.ssh_executor.execute("ls -ld /mnt/replica 2>&1")
        diag_lines.append(f"Mount point directory:\n{output}\n")

        success, output = self.ssh_executor.execute("ls -la /root/.smbcredentials 2>&1")
        diag_lines.append(f"Credentials file:\n{output}\n")

        if not win_host:
            diag_lines.append("[YELLOW]Windows host IP is not configured; skip ping[/YELLOW]\n")
        else:
            success, output = self.ssh_executor.execute(f"ping -c 1 -W 2 {win_host} 2>&1 || echo 'UNREACHABLE'")
            out = (output or "").lower()
            if "unreachable" in out or "100% packet loss" in out:
                diag_lines.append(f"[RED]Windows host ({win_host}) is unreachable[/RED]\n")
            else:
                diag_lines.append(f"[GREEN]Windows host ({win_host}) is reachable[/GREEN]\n")

        success, output = self.ssh_executor.execute("grep /mnt/replica /etc/fstab 2>&1 || echo 'No fstab entry'")
        diag_lines.append(f"/etc/fstab entry:\n{output}\n")

        return "\n".join(diag_lines)
    except Exception as exc:
        return f"Failed to collect diagnostics: {exc}"

