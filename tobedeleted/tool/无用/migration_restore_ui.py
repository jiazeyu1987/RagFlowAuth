# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "数据恢复工具（RagflowAuth）"
VERSION = "0.2.0"


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _docker_ok() -> tuple[bool, str]:
    code, out = _run(["docker", "info"])
    if code != 0:
        msg = out or "Docker 引擎不可用。"
        if "dockerDesktopLinuxEngine" in msg or "open //./pipe/dockerDesktopLinuxEngine" in msg:
            msg = (
                "Docker Desktop 的 Linux 引擎没有启动。\n\n"
                "请按下面步骤处理：\n"
                "1) 打开 Docker Desktop\n"
                "2) 等待右下角提示 'Docker is running'\n"
                "3) 如果正在使用 Windows 容器，请在 Docker Desktop 菜单选择 'Switch to Linux containers'\n"
                "4) 回到本工具，重新点击“数据恢复”\n\n"
                f"原始错误：{out}"
            )
        return False, msg
    code, out = _run(["docker", "compose", "version"])
    if code != 0:
        return False, out or "找不到 docker compose 命令。请升级 Docker Desktop。"
    return True, ""


def _normalize_backup_dir(selected: Path) -> Path:
    if (selected / "manifest.json").exists() and (selected / "auth.db").exists():
        return selected
    try:
        candidates = [p for p in selected.iterdir() if p.is_dir() and p.name.startswith("migration_pack_")]
    except Exception:
        return selected
    if len(candidates) == 1:
        child = candidates[0]
        if (child / "manifest.json").exists() and (child / "auth.db").exists():
            return child
    return selected


def _list_docker_volumes() -> list[str]:
    code, out = _run(["docker", "volume", "ls", "--format", "{{.Name}}"])
    if code != 0:
        raise RuntimeError(out or "无法读取 Docker volumes")
    return sorted([line.strip() for line in (out or "").splitlines() if line.strip()])


_VOL_ARCHIVE_RE = re.compile(r"^(?P<name>.+)_(?P<ts>\d{8}_\d{6})\.tar\.gz$")


def _infer_volume_name(archive_name: str) -> str:
    m = _VOL_ARCHIVE_RE.match(archive_name)
    if m:
        return m.group("name")
    if archive_name.endswith(".tar.gz"):
        return archive_name[: -len(".tar.gz")]
    return archive_name


def _pick_target_volume_name(archive_volume: str, existing: list[str]) -> tuple[str, str]:
    if archive_volume in existing:
        return archive_volume, "exact"
    suffix_matches = [v for v in existing if v.endswith(f"_{archive_volume}")]
    if len(suffix_matches) == 1:
        return suffix_matches[0], "suffix"
    # If backup was created under a different compose project name, volumes may differ only by prefix:
    # e.g. `docker_mysql_data` (backup) -> `ragflow_compose_mysql_data` (current).
    if "_" in archive_volume:
        volume_key = archive_volume.split("_", 1)[1]
        key_matches = [v for v in existing if v == volume_key or v.endswith(f"_{volume_key}")]
        if len(key_matches) == 1:
            return key_matches[0], "key"
    contains_matches = [v for v in existing if archive_volume in v]
    if len(contains_matches) == 1:
        return contains_matches[0], "contains"
    return archive_volume, "create"


def _ensure_volume(name: str) -> None:
    code, _ = _run(["docker", "volume", "inspect", name])
    if code == 0:
        return
    code, out = _run(["docker", "volume", "create", name])
    if code != 0:
        raise RuntimeError(f"创建 Docker volume 失败：{name}\n{out}")


def _restore_volume_from_tar(volume_name: str, tar_path: Path) -> None:
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/data",
        "-v",
        f"{str(tar_path.parent)}:/backup:ro",
        "alpine",
        "sh",
        "-lc",
        f"rm -rf /data/* && tar -xzf /backup/{tar_path.name} -C /data",
    ]
    code, out = _run(cmd)
    if code != 0:
        raise RuntimeError(f"恢复 volume 失败：{volume_name}\n{out}")


def _compose_down(compose_file: Path, *, cwd: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "down"], cwd=cwd)
    if code != 0:
        raise RuntimeError(out or "docker compose down 失败")


def _compose_up(compose_file: Path, *, cwd: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "up", "-d"], cwd=cwd)
    if code != 0:
        raise RuntimeError(out or "docker compose up 失败")


@dataclass(frozen=True)
class RestoreConfig:
    backup_dir: Path
    install_dir: Path


class RestoreApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("980x720")
        self.resizable(False, False)

        self.backup_dir_var = tk.StringVar(value="")
        self.install_dir_var = tk.StringVar(value=str(Path.home() / "RagflowAuth"))
        self.import_images_var = tk.BooleanVar(value=True)
        self.export_compose_var = tk.StringVar(value="")

        self._busy = False
        self._build_ui()

    def _build_ui(self) -> None:
        pad = 12
        root = tk.Frame(self, padx=pad, pady=pad)
        root.pack(fill="both", expand=True)

        tk.Label(root, text="选择备份目录 + 项目目录，然后一键恢复", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(
            root,
            text="会恢复 auth.db，并尝试恢复 RAGFlow volumes（可选导入镜像）。恢复会覆盖目标机器的 data/auth.db。",
            fg="#555555",
        ).pack(anchor="w", pady=(4, 14))

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="备份目录：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.backup_dir_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择…", width=10, command=self._pick_backup_dir).pack(side="left", padx=(8, 0))

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="项目目录：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.install_dir_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择…", width=10, command=self._pick_install_dir).pack(side="left", padx=(8, 0))

        actions = tk.Frame(root)
        actions.pack(fill="x", pady=(8, 8))
        tk.Button(actions, text="数据恢复", width=12, command=self._restore_clicked).pack(side="left")
        tk.Checkbutton(actions, text="同时导入备份里的 RAGFlow 镜像（推荐）", variable=self.import_images_var).pack(
            side="left", padx=(12, 0)
        )

        adv = tk.LabelFrame(root, text="高级：导出镜像到备份目录（可选）")
        adv.pack(fill="x", pady=(8, 8))

        row = tk.Frame(adv)
        row.pack(fill="x", pady=(6, 6))
        tk.Label(row, text="RAGFlow compose：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.export_compose_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择…", width=10, command=self._pick_ragflow_compose).pack(side="left", padx=(8, 0))
        tk.Button(row, text="导出镜像", width=10, command=self._export_images_clicked).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate")
        self.progress.pack(fill="x", pady=(6, 6))
        self.progress["value"] = 0

        self.status = tk.Label(root, text="", fg="#555555", anchor="w")
        self.status.pack(fill="x", pady=(6, 6))

        log_frame = tk.Frame(root, bd=1, relief="solid")
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=22, wrap="word")
        self.log.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(log_frame, command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set)

    def _pick_backup_dir(self) -> None:
        p = filedialog.askdirectory(title="选择备份目录（migration_pack_...）")
        if p:
            self.backup_dir_var.set(str(_normalize_backup_dir(Path(p))))

    def _pick_install_dir(self) -> None:
        p = filedialog.askdirectory(title="选择项目目录（RagflowAuth）")
        if p:
            self.install_dir_var.set(p)

    def _pick_ragflow_compose(self) -> None:
        p = filedialog.askopenfilename(
            title="选择 RAGFlow docker-compose.yml",
            filetypes=[("YAML", "*.yml *.yaml"), ("All", "*.*")],
        )
        if p:
            self.export_compose_var.set(p)

    def _append_log(self, msg: str) -> None:
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _set_status(self, msg: str, *, ok: bool = True) -> None:
        self.status.configure(text=msg, fg="#0f766e" if ok else "#b91c1c")

    def _set_progress(self, value: int) -> None:
        self.progress["value"] = max(0, min(100, int(value)))
        self.update_idletasks()

    def _restore_clicked(self) -> None:
        if self._busy:
            return
        threading.Thread(target=self._restore, daemon=True).start()

    def _export_images_clicked(self) -> None:
        if self._busy:
            return
        threading.Thread(target=self._export_images, daemon=True).start()

    def _list_compose_images(self, compose_file: Path) -> list[str]:
        code, out = _run(["docker", "compose", "-f", str(compose_file), "config", "--images"], cwd=compose_file.parent)
        if code != 0:
            raise RuntimeError(out or "无法从 docker compose 获取镜像列表（config --images）")
        return sorted({line.strip() for line in (out or "").splitlines() if line.strip()})

    def _export_images(self) -> None:
        self._busy = True
        self._set_progress(0)
        try:
            ok, why = _docker_ok()
            if not ok:
                self._set_status("Docker 不可用", ok=False)
                messagebox.showerror("Docker 不可用", why)
                return

            backup_dir = _normalize_backup_dir(Path(self.backup_dir_var.get() or "").expanduser())
            compose_file = Path((self.export_compose_var.get() or "").strip()).expanduser()
            if not (backup_dir / "manifest.json").exists():
                self._set_status("备份目录不正确", ok=False)
                messagebox.showerror("错误", "请先选择正确的 migration_pack 备份目录（里面应有 manifest.json）。")
                return
            if not compose_file.exists():
                self._set_status("compose 文件不存在", ok=False)
                messagebox.showerror("错误", "请选择有效的 RAGFlow docker-compose.yml。")
                return

            self._set_status("扫描镜像…")
            self._set_progress(10)
            images = self._list_compose_images(compose_file)
            if not images:
                raise RuntimeError("未解析到任何镜像（docker compose config --images 为空）")
            self._append_log(f"[{_now_str()}] 解析到 {len(images)} 个镜像：")
            for img in images:
                self._append_log(f"  - {img}")

            images_dir = backup_dir / "ragflow" / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            tar_path = images_dir / f"ragflow_images_{time.strftime('%Y%m%d_%H%M%S', time.localtime())}.tar"

            self._set_status("导出镜像（docker save）…")
            self._set_progress(35)
            code, out = _run(["docker", "save", "-o", str(tar_path), *images])
            if out:
                self._append_log(out)
            if code != 0:
                raise RuntimeError("docker save 失败，请查看日志输出。")

            self._set_progress(100)
            self._set_status("导出完成")
            self._append_log(f"[{_now_str()}] 已导出镜像：{tar_path}")
            messagebox.showinfo("完成", f"导出完成！\n\n已生成：\n{tar_path}")
        except Exception as e:
            self._set_status("导出失败", ok=False)
            self._append_log(f"[{_now_str()}] ERROR: {e}")
            messagebox.showerror("导出失败", str(e))
        finally:
            self._busy = False

    def _import_images_from_backup(self, backup_dir: Path) -> int:
        images_dir = backup_dir / "ragflow" / "images"
        if not images_dir.exists():
            return 0
        tars = sorted([p for p in images_dir.glob("*.tar") if p.is_file()])
        if not tars:
            return 0
        self._append_log(f"[{_now_str()}] 发现 {len(tars)} 个镜像包，将导入到本机 Docker：")
        for p in tars:
            self._append_log(f"  - {p.name}")
        for i, tar_path in enumerate(tars, start=1):
            self._append_log(f"[{_now_str()}] 导入镜像 {i}/{len(tars)}：{tar_path.name}")
            code, out = _run(["docker", "load", "-i", str(tar_path)])
            if out:
                self._append_log(out)
            if code != 0:
                raise RuntimeError(f"导入镜像失败：{tar_path}\n{out}")
        return len(tars)

    def _restore(self) -> None:
        self._busy = True
        self._set_progress(0)
        try:
            ok, why = _docker_ok()
            if not ok:
                self._set_status("Docker 不可用", ok=False)
                messagebox.showerror("Docker 不可用", why)
                return

            backup_dir = _normalize_backup_dir(Path(self.backup_dir_var.get() or "").expanduser())
            install_dir = Path(self.install_dir_var.get() or "").expanduser()

            manifest_path = backup_dir / "manifest.json"
            auth_db_src = backup_dir / "auth.db"
            ragflow_vols_dir = backup_dir / "ragflow" / "volumes"

            if not manifest_path.exists():
                self._set_status("备份目录不正确", ok=False)
                messagebox.showerror("错误", "备份目录里找不到 manifest.json，请重新选择。")
                return
            if not auth_db_src.exists():
                self._set_status("缺少 auth.db", ok=False)
                messagebox.showerror("错误", "备份目录里找不到 auth.db。")
                return
            if not install_dir.exists():
                self._set_status("项目目录不存在", ok=False)
                messagebox.showerror("错误", "项目目录不存在，请重新选择。")
                return

            if not messagebox.askyesno("确认", "恢复将覆盖目标机器 data/auth.db，并可能覆盖 RAGFlow volumes。\n\n是否继续？"):
                return

            cfg = RestoreConfig(backup_dir=backup_dir, install_dir=install_dir)
            self._append_log(f"[{_now_str()}] 开始恢复")
            self._append_log(f"[{_now_str()}] 备份目录：{cfg.backup_dir}")
            self._append_log(f"[{_now_str()}] 项目目录：{cfg.install_dir}")

            _ = json.loads(manifest_path.read_text(encoding="utf-8"))

            if bool(self.import_images_var.get()):
                self._set_status("导入 RAGFlow 镜像…")
                self._set_progress(5)
                imported = self._import_images_from_backup(cfg.backup_dir)
                if imported:
                    self._append_log(f"[{_now_str()}] 镜像导入完成：{imported} 个")
                else:
                    self._append_log(f"[{_now_str()}] 未找到 ragflow/images/*.tar（跳过镜像导入）")

            # Stop our app
            self._set_status("停止本系统容器…")
            self._set_progress(12)
            app_compose = cfg.install_dir / "docker" / "docker-compose.yml"
            if not app_compose.exists():
                raise RuntimeError(f"找不到本系统 compose 文件：{app_compose}")
            try:
                self._append_log(f"[{_now_str()}] 停止本系统：docker compose down")
                _compose_down(app_compose, cwd=cfg.install_dir)
            except Exception as e:
                if not messagebox.askyesno("提示", f"停止本系统失败，仍要继续恢复吗？\n\n{e}"):
                    return

            # Restore auth.db
            self._set_status("恢复 auth.db…")
            self._set_progress(25)
            auth_db_dst = cfg.install_dir / "data" / "auth.db"
            auth_db_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(auth_db_src, auth_db_dst)
            self._append_log(f"[{_now_str()}] 已覆盖：{auth_db_dst}")

            # Restore ragflow volumes
            if ragflow_vols_dir.exists():
                archives = sorted([p for p in ragflow_vols_dir.glob("*.tar.gz") if p.is_file()])
                if archives:
                    self._set_status("恢复 RAGFlow volumes…")
                    self._append_log(f"[{_now_str()}] 发现 {len(archives)} 个 volume 备份包")
                    self._append_log(f"[{_now_str()}] 建议：先停止 RAGFlow 再恢复（避免写入冲突）。")

                    existing_vols = _list_docker_volumes()
                    if not existing_vols:
                        self._append_log(
                            f"[{_now_str()}] 提示：当前机器还没有任何 Docker volumes。"
                            "如果你还没在新机器启动过 RAGFlow，建议先启动一次 RAGFlow（让它创建 volumes），再运行恢复会更准确。"
                        )

                    base = 35
                    span = 55
                    for i, tar_path in enumerate(archives, start=1):
                        archive_vol = _infer_volume_name(tar_path.name)
                        target_vol, reason = _pick_target_volume_name(archive_vol, existing_vols)
                        self._append_log(
                            f"[{_now_str()}] 恢复 volume {i}/{len(archives)}：{archive_vol} -> {target_vol}（{reason}）"
                        )
                        _ensure_volume(target_vol)
                        _restore_volume_from_tar(target_vol, tar_path)
                        self._set_progress(base + int(span * i / max(1, len(archives))))

                    self._append_log(f"[{_now_str()}] RAGFlow volumes 已恢复：请重启一次 RAGFlow。")
                else:
                    self._append_log(f"[{_now_str()}] 未找到 ragflow/volumes/*.tar.gz（跳过 RAGFlow 恢复）")
            else:
                self._append_log(f"[{_now_str()}] 未找到 ragflow/volumes 目录（跳过 RAGFlow 恢复）")

            # Start our app
            self._set_status("启动本系统容器…")
            self._set_progress(92)
            _compose_up(app_compose, cwd=cfg.install_dir)
            self._append_log(f"[{_now_str()}] 已启动本系统容器")

            self._set_progress(100)
            self._set_status("恢复完成")
            messagebox.showinfo("完成", "恢复完成！\n\n已恢复 auth.db，并已尝试恢复 RAGFlow volumes/镜像。")
        except Exception as e:
            self._set_status("恢复失败", ok=False)
            self._append_log(f"[{_now_str()}] ERROR: {e}")
            messagebox.showerror("恢复失败", str(e))
        finally:
            self._busy = False


def main() -> int:
    app = RestoreApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
