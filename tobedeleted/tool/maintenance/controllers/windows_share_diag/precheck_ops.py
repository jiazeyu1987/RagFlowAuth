def pre_mount_diagnostic_impl(app):
    self = app
    """Collect pre-mount diagnostics for Windows SMB share."""
    try:
        diag_lines = []
        win_host = (self.config.windows_share_host or "").strip()

        print("[DIAG] 1. check mount point directory...", flush=True)
        success, output = self.ssh_executor.execute("ls -ld /mnt/replica 2>&1")
        mount_dir = output.strip() if output.strip() else "missing"
        diag_lines.append(f"1. Mount point directory: {mount_dir}")

        print("[DIAG] 2. check leftover mount...", flush=True)
        success, output = self.ssh_executor.execute("mount | grep /mnt/replica")
        if success and output.strip():
            diag_lines.append(f"2. [RED]Found leftover mount:[/RED]\n{output.strip()}")
            diag_lines.append("   Suggestion: unmount Windows share first.")
        else:
            diag_lines.append("2. [GREEN]No leftover mount[/GREEN]")

        print("[DIAG] 3. check mount point lock process...", flush=True)
        success, output = self.ssh_executor.execute("fuser /mnt/replica 2>&1 || echo 'NO_PROCESS'")
        if "no process" in output.lower() or "NO_PROCESS" in output:
            diag_lines.append("3. [GREEN]No process is locking mount point[/GREEN]")
        else:
            diag_lines.append(f"3. [RED]Processes using mount point:[/RED]\n{output.strip()}")

        print("[DIAG] 4. test ICMP connectivity...", flush=True)
        if not win_host:
            diag_lines.append("4. [YELLOW]Windows host IP is not configured; skip ping[/YELLOW]")
        else:
            success, output = self.ssh_executor.execute(f"ping -c 2 -W 2 {win_host} 2>&1")
            out = (output or "").lower()
            if "100% packet loss" in out or "unreachable" in out:
                diag_lines.append(f"4. [RED]ICMP unreachable (ping {win_host} failed)[/RED]")
            else:
                diag_lines.append(f"4. [GREEN]ICMP reachable (ping {win_host} ok)[/GREEN]")

        print("[DIAG] 5. test TCP port 445...", flush=True)
        if not win_host:
            diag_lines.append("5. [YELLOW]Windows host IP is not configured; skip TCP/445 check[/YELLOW]")
        else:
            port_test_cmd = (
                f"timeout 3 bash -c 'echo > /dev/tcp/{win_host}/445' 2>&1 "
                "&& echo 'PORT_OK' || echo 'PORT_FAIL'"
            )
            success, output = self.ssh_executor.execute(port_test_cmd)
            if "PORT_OK" in (output or ""):
                diag_lines.append(f"5. [GREEN]TCP 445 reachable ({win_host} SMB is available)[/GREEN]")
            else:
                diag_lines.append(f"5. [RED]TCP 445 unreachable ({win_host} SMB is not available)[/RED]")
                diag_lines.append("   Possible reasons: firewall/SMB disabled/host offline.")

        print("[DIAG] 6. check credentials file...", flush=True)
        success, output = self.ssh_executor.execute("ls -la /root/.smbcredentials 2>&1")
        if success and ".smbcredentials" in (output or ""):
            diag_lines.append("6. [GREEN]Credentials file exists[/GREEN]")
        else:
            diag_lines.append("6. [YELLOW]Credentials file missing (will be created automatically)[/YELLOW]")

        print("[DIAG] 7. check cifs-utils...", flush=True)
        success, output = self.ssh_executor.execute("which mount.cifs 2>&1")
        if success:
            diag_lines.append("7. [GREEN]cifs-utils installed[/GREEN]")
        else:
            diag_lines.append("7. [RED]cifs-utils missing[/RED]")
            diag_lines.append("   Fix: yum install cifs-utils -y")

        print("[DIAG] completed", flush=True)
        return "\n".join(diag_lines)

    except Exception as exc:
        error_msg = f"Diagnostic failed: {exc}"
        print(f"[DIAG] ERROR: {error_msg}", flush=True)
        return error_msg

