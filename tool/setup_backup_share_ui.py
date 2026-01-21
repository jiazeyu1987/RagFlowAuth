from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin() -> None:
    params = " ".join([f'"{a}"' for a in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


def _run_powershell(command: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _ps_escape_single_quotes(s: str) -> str:
    return s.replace("'", "''")


def _ensure_firewall_file_sharing_rules() -> None:
    """
    Enables Windows firewall rules required for SMB file sharing.

    Notes:
    - On non-English Windows, DisplayGroup is localized, so we try multiple names.
    - If the built-in group doesn't exist, we create Private-profile inbound rules for SMB ports.
    """
    cmd = r"""
    $ErrorActionPreference='Stop'
    $groups = @('File and Printer Sharing','文件和打印机共享')
    $rules = @()
    foreach ($g in $groups) {
      try { $rules += Get-NetFirewallRule -DisplayGroup $g -ErrorAction Stop } catch { }
    }
    if (-not $rules -or $rules.Count -eq 0) {
      # Fallback: try by internal Group id patterns / display name patterns
      $rules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
        ($_.Group -match 'FileAndPrinterSharing') -or
        ($_.DisplayGroup -match 'File and Printer Sharing') -or
        ($_.DisplayGroup -match '文件和打印机共享') -or
        ($_.DisplayName -match 'File and Printer Sharing') -or
        ($_.DisplayName -match '文件和打印机共享')
      }
    }

    if ($rules -and $rules.Count -gt 0) {
      $rules | Enable-NetFirewallRule | Out-Null
      return
    }

    # Last resort: create minimal inbound rules for SMB (Private profile only)
    function Ensure-Rule($name, $proto, $ports) {
      $existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
      if (-not $existing) {
        New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Profile Private -Protocol $proto -LocalPort $ports | Out-Null
      } else {
        $existing | Enable-NetFirewallRule | Out-Null
      }
    }

    Ensure-Rule 'RagflowAuth Backup SMB (TCP 445)' TCP 445
    Ensure-Rule 'RagflowAuth Backup SMB (TCP 139)' TCP 139
    Ensure-Rule 'RagflowAuth Backup SMB (UDP 137)' UDP 137
    Ensure-Rule 'RagflowAuth Backup SMB (UDP 138)' UDP 138
    """
    code, out = _run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"无法配置防火墙文件共享规则：\n{out}")


@dataclass(frozen=True)
class ShareConfig:
    folder: str
    share_name: str
    allow_account: str
    access_right: str  # Read | Change | Full


def _apply_share(cfg: ShareConfig) -> None:
    folder = os.path.abspath(cfg.folder)
    if not os.path.isdir(folder):
        raise RuntimeError("请选择一个存在的文件夹。")

    share_name = cfg.share_name.strip()
    if not share_name:
        raise RuntimeError("共享名不能为空。")

    allow_account = cfg.allow_account.strip() or "Everyone"
    access_right = cfg.access_right.strip() or "Change"
    if access_right not in {"Read", "Change", "Full"}:
        raise RuntimeError("访问权限必须是 Read / Change / Full。")

    folder_ps = _ps_escape_single_quotes(folder)
    share_ps = _ps_escape_single_quotes(share_name)
    account_ps = _ps_escape_single_quotes(allow_account)

    # 1) Ensure LanmanServer is running (SMB server).
    cmd = f"""
    $ErrorActionPreference='Stop'
    Set-Service -Name LanmanServer -StartupType Automatic
    Start-Service -Name LanmanServer
    """
    code, out = _run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"无法启动文件共享服务（LanmanServer）：\n{out}")

    # 2) Create or update share
    # If share exists and points elsewhere, remove and recreate.
    cmd = f"""
    $ErrorActionPreference='Stop'
    $name='{share_ps}'
    $path='{folder_ps}'
    $existing = Get-SmbShare -Name $name -ErrorAction SilentlyContinue
    if ($existing) {{
      if ($existing.Path -ne $path) {{
        Remove-SmbShare -Name $name -Force
        $existing = $null
      }}
    }}
    if (-not $existing) {{
      New-SmbShare -Name $name -Path $path -CachingMode None | Out-Null
    }}
    """
    code, out = _run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"无法创建/更新共享：\n{out}")

    # 3) Grant share permissions
    cmd = f"""
    $ErrorActionPreference='Stop'
    $name='{share_ps}'
    $account='{account_ps}'
    $right='{access_right}'
    Grant-SmbShareAccess -Name $name -AccountName $account -AccessRight $right -Force | Out-Null
    """
    code, out = _run_powershell(cmd)
    if code != 0:
        raise RuntimeError(f"无法设置共享权限：\n{out}")

    # 4) Ensure NTFS permissions allow writing (for backup destination).
    # Map share right to NTFS right:
    # - Read => RX
    # - Change => M
    # - Full => F
    ntfs_right = {"Read": "RX", "Change": "M", "Full": "F"}[access_right]
    cmd = ["cmd", "/c", "icacls", folder, "/grant", f"{allow_account}:(OI)(CI){ntfs_right}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        out = (proc.stdout or "") + (proc.stderr or "")
        raise RuntimeError(f"无法设置文件夹权限（NTFS）：\n{out.strip()}")

    # 5) Enable firewall rules for file sharing (locale-aware + fallback)
    _ensure_firewall_file_sharing_rules()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("备份共享目录设置")
        self.geometry("760x420")
        self.resizable(False, False)

        self.folder_var = tk.StringVar(value="")
        self.share_var = tk.StringVar(value="backup")
        self.account_var = tk.StringVar(value="Everyone")
        self.right_var = tk.StringVar(value="Change")

        self._build()

    def _build(self) -> None:
        pad = 10
        frame = tk.Frame(self, padx=pad, pady=pad)
        frame.pack(fill="both", expand=True)

        title = tk.Label(frame, text="把一个文件夹设置为“接收备份”的共享目录", font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w")

        hint = tk.Label(
            frame,
            text="提示：需要管理员权限。设置完成后，服务器可以写入 \\\\这台电脑\\共享名\\子目录",
            fg="#555555",
            justify="left",
        )
        hint.pack(anchor="w", pady=(4, 14))

        row1 = tk.Frame(frame)
        row1.pack(fill="x")
        tk.Label(row1, text="备份文件夹：", width=12, anchor="w").pack(side="left")
        tk.Entry(row1, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        tk.Button(row1, text="选择…", command=self._pick_folder, width=10).pack(side="left", padx=(8, 0))

        row2 = tk.Frame(frame)
        row2.pack(fill="x", pady=(12, 0))
        tk.Label(row2, text="共享名：", width=12, anchor="w").pack(side="left")
        tk.Entry(row2, textvariable=self.share_var, width=24).pack(side="left")

        row3 = tk.Frame(frame)
        row3.pack(fill="x", pady=(12, 0))
        tk.Label(row3, text="允许访问账号：", width=12, anchor="w").pack(side="left")
        tk.Entry(row3, textvariable=self.account_var, width=24).pack(side="left")
        tk.Label(row3, text="（默认 Everyone；更安全可填具体用户）", fg="#555555").pack(side="left", padx=(8, 0))

        row4 = tk.Frame(frame)
        row4.pack(fill="x", pady=(12, 0))
        tk.Label(row4, text="访问权限：", width=12, anchor="w").pack(side="left")
        opt = tk.OptionMenu(row4, self.right_var, "Read", "Change", "Full")
        opt.config(width=10)
        opt.pack(side="left")
        tk.Label(row4, text="（备份建议 Change 或 Full）", fg="#555555").pack(side="left", padx=(8, 0))

        self.status = tk.Label(frame, text="", fg="#0f766e", justify="left")
        self.status.pack(anchor="w", pady=(16, 0))

        btn_row = tk.Frame(frame)
        btn_row.pack(fill="x", pady=(16, 0))
        tk.Button(btn_row, text="设置为备份共享目录", command=self._apply, height=2).pack(side="left")
        tk.Button(btn_row, text="关闭", command=self.destroy, height=2, width=10).pack(side="right")

        self.output = tk.Text(frame, height=8, wrap="word")
        self.output.pack(fill="both", expand=True, pady=(16, 0))
        self.output.configure(state="disabled")

    def _pick_folder(self) -> None:
        d = filedialog.askdirectory(title="选择备份文件夹")
        if d:
            self.folder_var.set(d)

    def _write_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", text)
        self.output.configure(state="disabled")

    def _apply(self) -> None:
        if not _is_admin():
            if messagebox.askyesno("需要管理员权限", "这个操作需要管理员权限。是否用管理员权限重新打开？"):
                _relaunch_as_admin()
                self.destroy()
            return

        cfg = ShareConfig(
            folder=self.folder_var.get(),
            share_name=self.share_var.get(),
            allow_account=self.account_var.get(),
            access_right=self.right_var.get(),
        )
        try:
            self.status.configure(text="正在设置共享，请稍等…", fg="#0f766e")
            self.update_idletasks()

            _apply_share(cfg)

            host = socket.gethostname()
            share = cfg.share_name.strip()
            folder = os.path.abspath(cfg.folder)
            msg = (
                "设置成功。\n\n"
                f"本机路径：{folder}\n"
                f"共享路径：\\\\{host}\\{share}\n\n"
                "下一步（在服务器那台电脑）：\n"
                f"- 在“数据安全”里填写目标电脑 IP（或主机名）、共享名 {share}，以及子目录（可空）。\n"
            )
            self.status.configure(text="设置成功。", fg="#059669")
            self._write_output(msg)
        except Exception as exc:
            self.status.configure(text="设置失败。", fg="#b91c1c")
            self._write_output(
                f"{exc}\n\n"
                "提示：如果这是公司电脑且组策略限制了防火墙/共享设置，可能需要 IT 管理员协助放行。"
            )


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
