# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

APP_NAME = "一键部署（从发布包 ZIP）"
VERSION = "0.5.0"


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


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
                "4) 回到本工具，点击“检查 Docker”再点击“一键部署”\n\n"
                f"原始错误：{out}"
            )
        return False, msg

    code, out = _run(["docker", "compose", "version"])
    if code != 0:
        return False, out or "找不到 docker compose 命令。请升级 Docker Desktop。"

    return True, ""


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


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


def _detect_bundled_migration_pack(install_dir: Path) -> Path | None:
    candidate = install_dir / "migration_pack"
    if (candidate / "manifest.json").exists() and (candidate / "auth.db").exists():
        return candidate
    return None


def _detect_bundled_ragflow_compose(install_dir: Path) -> Path | None:
    candidate = install_dir / "ragflow_compose" / "docker-compose.yml"
    if candidate.exists():
        return candidate
    # backward compat
    candidate2 = install_dir / "ragflow" / "docker-compose.yml"
    if candidate2.exists():
        return candidate2
    return None


def _read_ragflow_config(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _compose_down(compose_file: Path, *, cwd: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "down"], cwd=cwd)
    if code != 0:
        raise RuntimeError(out or "docker compose down 失败")


def _compose_down_ignore_errors(compose_file: Path, *, cwd: Path, log: callable) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "down"], cwd=cwd)
    if out:
        log(out)
    if code != 0:
        log(f"[{_now_str()}] 警告：docker compose down 失败（将继续）：{out or 'unknown error'}")


def _compose_up_build(compose_file: Path, *, cwd: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "up", "-d", "--build"], cwd=cwd)
    if code != 0:
        raise RuntimeError(out or "docker compose up -d --build 失败")


def _compose_up(compose_file: Path, *, cwd: Path) -> str:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "up", "-d"], cwd=cwd)
    if code != 0:
        raise RuntimeError(out or "docker compose up -d 失败")
    return out


def _compose_stop(compose_file: Path, *, cwd: Path) -> str:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "stop"], cwd=cwd)
    if code != 0:
        raise RuntimeError(out or "docker compose stop 失败")
    return out


def _compose_start(compose_file: Path, *, cwd: Path) -> str:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "start"], cwd=cwd)
    if code != 0:
        raise RuntimeError(out or "docker compose start 失败")
    return out


def _ragflow_running() -> bool:
    code, out = _run(["docker", "ps", "--format", "{{.Image}} {{.Names}}"])
    if code != 0:
        return False
    return "ragflow" in (out or "").lower()


def _ensure_ragflow_started(compose_file: Path, *, log: callable) -> None:
    if _ragflow_running():
        log(f"[{_now_str()}] 检测到 Docker 中已存在 RAGFlow 容器：跳过安装/启动")
        return

    if not compose_file.exists():
        raise RuntimeError(f"找不到 RAGFlow docker-compose.yml：{compose_file}")

    log(f"[{_now_str()}] 未检测到 RAGFlow 容器，开始启动 RAGFlow：{compose_file}")
    try:
        # Always cleanup stale resources first to avoid "container name already in use".
        _compose_down_ignore_errors(compose_file, cwd=compose_file.parent, log=log)
        out = _compose_up(compose_file, cwd=compose_file.parent)
        if out:
            log(out)

        code, ps_out = _run(["docker", "compose", "-f", str(compose_file), "ps"], cwd=compose_file.parent)
        if ps_out:
            log(ps_out)
        if code != 0:
            log(f"[{_now_str()}] 警告：docker compose ps 返回非 0（可能尚未启动完成）")
    except Exception as e:
        s = str(e)
        if "already in use by container" in s or "Conflict. The container name" in s:
            raise RuntimeError(
                "启动 RAGFlow 失败：检测到“容器名冲突”。\n\n"
                "请按下面步骤处理（在 ragflow_compose 目录运行）：\n"
                "1) docker compose down\n"
                "2) 再回到安装器点“一键部署”或在该目录执行 docker compose up -d\n\n"
                f"详细错误：{e}"
            )
        raise RuntimeError(
            "启动 RAGFlow 失败。\n\n"
            "常见原因：RAGFlow 的 docker-compose.yml 依赖同目录下的其它文件（例如 docker-compose-base.yml、.env 等），"
            "请把 RAGFlow 的整个 compose 目录完整拷贝到同一个文件夹再重试。\n\n"
            f"详细错误：{e}"
        )


def _ensure_ragflow_volumes_exist_then_stop(compose_file: Path, *, log: callable) -> None:
    """
    To restore to the correct *prefixed* volumes (e.g. ragflow_compose_esdata01),
    we need compose to create those volumes first, then stop containers before restoring.
    """
    if not compose_file.exists():
        raise RuntimeError(f"找不到 RAGFlow docker-compose.yml：{compose_file}")

    log(f"[{_now_str()}] 先执行 docker compose down（清理旧容器/网络，避免冲突）")
    _compose_down_ignore_errors(compose_file, cwd=compose_file.parent, log=log)

    if not _ragflow_running():
        log(f"[{_now_str()}] 启动一次 RAGFlow（用于创建正确的 volumes）")
        _ensure_ragflow_started(compose_file, log=log)

    log(f"[{_now_str()}] 停止 RAGFlow（避免写入冲突）")
    out = _compose_stop(compose_file, cwd=compose_file.parent)
    if out:
        log(out)


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


def _import_images_from_backup(backup_dir: Path) -> list[Path]:
    images_dir = backup_dir / "ragflow" / "images"
    if not images_dir.exists():
        return []
    return sorted([p for p in images_dir.glob("*.tar") if p.is_file()])


def _restore_from_migration_pack(backup_dir: Path, install_dir: Path, log: callable) -> None:
    backup_dir = _normalize_backup_dir(backup_dir)
    manifest = backup_dir / "manifest.json"
    auth_db = backup_dir / "auth.db"
    if not manifest.exists() or not auth_db.exists():
        raise RuntimeError("迁移包目录不正确：缺少 manifest.json 或 auth.db")

    compose = install_dir / "docker" / "docker-compose.yml"
    if not compose.exists():
        raise RuntimeError(f"找不到本系统 compose：{compose}")

    try:
        log(f"[{_now_str()}] 停止本系统（如已运行）：docker compose down")
        _compose_down(compose, cwd=install_dir)
    except Exception as e:
        log(f"[{_now_str()}] 警告：停止本系统失败（将继续）：{e}")

    dst_db = install_dir / "data" / "auth.db"
    dst_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(auth_db, dst_db)
    log(f"[{_now_str()}] 已恢复数据库：{dst_db}")

    image_tars = _import_images_from_backup(backup_dir)
    if image_tars:
        log(f"[{_now_str()}] 发现 {len(image_tars)} 个镜像包，将导入到本机 Docker：")
        for p in image_tars:
            log(f"  - {p.name}")
        for p in image_tars:
            log(f"[{_now_str()}] docker load：{p.name}")
            code, out = _run(["docker", "load", "-i", str(p)])
            if out:
                log(out)
            if code != 0:
                raise RuntimeError(f"导入镜像失败：{p}\n{out}")
    else:
        log(f"[{_now_str()}] 未找到 ragflow/images/*.tar（跳过镜像导入）")

    vols_dir = backup_dir / "ragflow" / "volumes"
    if not vols_dir.exists():
        log(f"[{_now_str()}] 未找到 ragflow/volumes（跳过 RAGFlow volume 恢复）")
        return
    archives = sorted([p for p in vols_dir.glob("*.tar.gz") if p.is_file()])
    if not archives:
        log(f"[{_now_str()}] 未找到 ragflow/volumes/*.tar.gz（跳过 RAGFlow volume 恢复）")
        return

    existing = _list_docker_volumes()
    if not existing:
        log(
            f"[{_now_str()}] 提示：当前机器还没有任何 Docker volumes。"
            "如果你还没在新机器启动过 RAGFlow，建议先启动一次 RAGFlow（让它创建 volumes），再恢复会更准确。"
        )

    log(f"[{_now_str()}] 开始恢复 RAGFlow volumes（{len(archives)} 个）")
    for i, tar_path in enumerate(archives, start=1):
        archive_vol = _infer_volume_name(tar_path.name)
        target_vol, reason = _pick_target_volume_name(archive_vol, existing)
        log(f"[{_now_str()}] volume {i}/{len(archives)}：{archive_vol} -> {target_vol}（{reason}）")
        _ensure_volume(target_vol)
        _restore_volume_from_tar(target_vol, tar_path)

    log(f"[{_now_str()}] RAGFlow volumes 已恢复：请重启一次 RAGFlow。")


@dataclass(frozen=True)
class InstallConfig:
    zip_path: Path
    install_dir: Path
    ragflow_base_url: str
    ragflow_api_key: str
    jwt_secret_key: str
    migration_dir: Path | None
    restore_after_install: bool
    start_ragflow_if_missing: bool
    ragflow_compose_path: Path | None


class InstallerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("980x820")
        self.resizable(False, False)

        self.zip_var = tk.StringVar(value="")
        self.install_dir_var = tk.StringVar(value=str(Path.home() / "RagflowAuth"))
        self.rag_base_var = tk.StringVar(value="http://127.0.0.1:9380")
        self.rag_key_var = tk.StringVar(value="")
        self.jwt_var = tk.StringVar(value="")

        self.migration_dir_var = tk.StringVar(value="")
        self.restore_var = tk.BooleanVar(value=True)

        self.start_ragflow_var = tk.BooleanVar(value=True)
        self.ragflow_compose_var = tk.StringVar(value="")

        self._busy = False
        self._build_ui()
        self._set_default_jwt()
        self._append_log(f"[{_now_str()}] {APP_NAME} v{VERSION}")

    def _build_ui(self) -> None:
        pad = 12
        root = tk.Frame(self, padx=pad, pady=pad)
        root.pack(fill="both", expand=True)

        tk.Label(root, text="从发布包 ZIP 一键部署（前端 + 后端 + RAGFlow 可选）", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(
            root,
            text="会把 ZIP 解压到目标目录，并执行 docker compose 启动。需要 Docker Desktop 已安装并在运行。",
            fg="#555555",
        ).pack(anchor="w", pady=(4, 14))

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="发布包 ZIP：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.zip_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择…", width=10, command=self._pick_zip).pack(side="left", padx=(8, 0))

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="安装目录：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.install_dir_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择…", width=10, command=self._pick_dir).pack(side="left", padx=(8, 0))

        tk.Label(root, text="RAGFlow 连接配置（会写入 ragflow_config.json）", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 6))

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="RAGFlow 地址：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.rag_base_var).pack(side="left", fill="x", expand=True)

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="RAGFlow API Key：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.rag_key_var).pack(side="left", fill="x", expand=True)

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Label(row, text="JWT 密钥：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.jwt_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="重新生成", width=10, command=self._set_default_jwt).pack(side="left", padx=(8, 0))

        tk.Label(root, text="可选：恢复迁移包数据（如果发布包里包含 migration_pack 会自动识别）", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(10, 6)
        )

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="迁移包目录：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.migration_dir_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择…", width=10, command=self._pick_migration_dir).pack(side="left", padx=(8, 0))

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Checkbutton(row, text="部署后自动恢复迁移包（会覆盖 data/auth.db 并可能覆盖 RAGFlow volumes）", variable=self.restore_var).pack(
            anchor="w"
        )

        tk.Label(root, text="可选：安装/启动 RAGFlow（如果发布包里包含 ragflow_compose 会自动识别）", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(10, 6)
        )

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="RAGFlow compose：", width=12, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.ragflow_compose_var).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择…", width=10, command=self._pick_ragflow_compose).pack(side="left", padx=(8, 0))

        row = tk.Frame(root)
        row.pack(fill="x", pady=(0, 10))
        tk.Checkbutton(
            row,
            text="如果 Docker 里没有 RAGFlow，则用上面的 compose 自动启动（有则跳过）",
            variable=self.start_ragflow_var,
        ).pack(anchor="w")

        actions = tk.Frame(root)
        actions.pack(fill="x", pady=(8, 8))
        tk.Button(actions, text="检查 Docker", width=12, command=self._check_docker).pack(side="left")
        tk.Button(actions, text="一键部署", width=12, command=self._deploy_clicked).pack(side="left", padx=(8, 0))

        self.status = tk.Label(root, text="", fg="#555555", anchor="w")
        self.status.pack(fill="x", pady=(6, 6))

        log_frame = tk.Frame(root, bd=1, relief="solid")
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=20, wrap="word")
        self.log.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(log_frame, command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set)

    def _pick_zip(self) -> None:
        p = filedialog.askopenfilename(title="选择发布包 ZIP", filetypes=[("ZIP", "*.zip")])
        if not p:
            return
        self.zip_var.set(p)

        # Best effort prefill base_url/api_key from ragflow_config.json inside ZIP (if present).
        try:
            with zipfile.ZipFile(p, "r") as zf:
                if "ragflow_config.json" in zf.namelist():
                    raw = json.loads(zf.read("ragflow_config.json").decode("utf-8"))
                    base = (raw.get("base_url") or "").strip()
                    key = (raw.get("api_key") or "").strip()
                    if base and (self.rag_base_var.get() or "").strip() in {"", "http://127.0.0.1:9380"}:
                        self.rag_base_var.set(base)
                    if key and not (self.rag_key_var.get() or "").strip():
                        self.rag_key_var.set(key)
        except Exception:
            pass

    def _pick_dir(self) -> None:
        p = filedialog.askdirectory(title="选择安装目录")
        if p:
            self.install_dir_var.set(p)

    def _pick_migration_dir(self) -> None:
        p = filedialog.askdirectory(title="选择迁移包目录（migration_pack_...）")
        if p:
            self.migration_dir_var.set(str(_normalize_backup_dir(Path(p))))

    def _pick_ragflow_compose(self) -> None:
        p = filedialog.askopenfilename(
            title="选择 RAGFlow docker-compose.yml",
            filetypes=[("YAML", "*.yml *.yaml"), ("All", "*.*")],
        )
        if p:
            self.ragflow_compose_var.set(p)

    def _append_log(self, msg: str) -> None:
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _set_status(self, msg: str, *, ok: bool = True) -> None:
        self.status.configure(text=msg, fg="#0f766e" if ok else "#b91c1c")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy

    def _set_default_jwt(self) -> None:
        if not (self.jwt_var.get() or "").strip():
            self.jwt_var.set(secrets.token_urlsafe(48))

    def _check_docker(self) -> None:
        ok, why = _docker_ok()
        if ok:
            self._set_status("Docker OK")
            code, out = _run(["docker", "version"])
            self._append_log(out or "(no output)")
        else:
            self._set_status("Docker 不可用", ok=False)
            messagebox.showerror("Docker 不可用", why)

    def _deploy_clicked(self) -> None:
        if self._busy:
            return
        threading.Thread(target=self._deploy, daemon=True).start()

    def _deploy(self) -> None:
        self._set_busy(True)
        try:
            ok, why = _docker_ok()
            if not ok:
                self._set_status("Docker 不可用", ok=False)
                messagebox.showerror("Docker 不可用", why)
                return

            zip_path = Path(self.zip_var.get() or "").expanduser()
            install_dir = Path(self.install_dir_var.get() or "").expanduser()
            if not zip_path.exists():
                self._set_status("ZIP 不存在", ok=False)
                messagebox.showerror("错误", "发布包 ZIP 不存在，请重新选择。")
                return

            rag_base = (self.rag_base_var.get() or "").strip()
            rag_key = (self.rag_key_var.get() or "").strip()
            jwt = (self.jwt_var.get() or "").strip()
            if not rag_base:
                self._set_status("RAGFlow 地址为空", ok=False)
                messagebox.showerror("错误", "请填写 RAGFlow 地址。")
                return
            if not jwt:
                jwt = secrets.token_urlsafe(48)
                self.jwt_var.set(jwt)

            migration_dir_txt = (self.migration_dir_var.get() or "").strip()
            migration_dir = Path(migration_dir_txt).expanduser() if migration_dir_txt else None

            start_ragflow = bool(self.start_ragflow_var.get())
            ragflow_compose_txt = (self.ragflow_compose_var.get() or "").strip()
            ragflow_compose_path = Path(ragflow_compose_txt).expanduser() if ragflow_compose_txt else None

            if not rag_key:
                # We may auto-fill from extracted ragflow_config.json later; allow continue here.
                pass

            cfg = InstallConfig(
                zip_path=zip_path,
                install_dir=install_dir,
                ragflow_base_url=rag_base,
                ragflow_api_key=rag_key,
                jwt_secret_key=jwt,
                migration_dir=migration_dir,
                restore_after_install=False,  # set after extraction
                start_ragflow_if_missing=start_ragflow,
                ragflow_compose_path=ragflow_compose_path,
            )

            self._extract_zip(cfg)

            # Auto-read api_key/base_url from extracted ragflow_config.json if user didn't fill them.
            extracted = _read_ragflow_config(cfg.install_dir / "ragflow_config.json")
            extracted_key = (extracted.get("api_key") or "").strip()
            extracted_base = (extracted.get("base_url") or "").strip()
            if extracted_base and (self.rag_base_var.get() or "").strip() in {"", "http://127.0.0.1:9380"}:
                self.rag_base_var.set(extracted_base)
            if extracted_key and not (self.rag_key_var.get() or "").strip():
                self.rag_key_var.set(extracted_key)

            rag_base = (self.rag_base_var.get() or "").strip()
            rag_key = (self.rag_key_var.get() or "").strip()
            cfg = InstallConfig(**{**cfg.__dict__, "ragflow_base_url": rag_base, "ragflow_api_key": rag_key})

            # Detect bundled migration pack / ragflow compose (from ZIP) if not selected.
            bundled_mig = _detect_bundled_migration_pack(cfg.install_dir)
            if cfg.migration_dir is None and bundled_mig is not None:
                cfg = InstallConfig(**{**cfg.__dict__, "migration_dir": bundled_mig})
                self.migration_dir_var.set(str(bundled_mig))

            bundled_compose = _detect_bundled_ragflow_compose(cfg.install_dir)
            if cfg.ragflow_compose_path is None and bundled_compose is not None:
                cfg = InstallConfig(**{**cfg.__dict__, "ragflow_compose_path": bundled_compose})
                self.ragflow_compose_var.set(str(bundled_compose))

            cfg = InstallConfig(
                **{**cfg.__dict__, "restore_after_install": bool(self.restore_var.get()) and cfg.migration_dir is not None}
            )

            # Now we can decide if api_key is allowed to be empty.
            if not cfg.ragflow_api_key:
                if not messagebox.askyesno("确认", "RAGFlow API Key 为空，仍要继续部署吗？（后端可能无法连接 RAGFlow）"):
                    return

            self._write_configs(cfg)

            # Correct restore order:
            # 1) Create compose-prefixed RAGFlow volumes (and stop) so restore maps to the correct targets.
            if cfg.restore_after_install and cfg.migration_dir is not None and cfg.ragflow_compose_path is not None:
                self._set_status("准备 RAGFlow（创建 volumes）…")
                self._append_log(f"[{_now_str()}] 准备 RAGFlow：创建 volumes 并停止")
                _ensure_ragflow_volumes_exist_then_stop(cfg.ragflow_compose_path, log=self._append_log)

            if cfg.restore_after_install and cfg.migration_dir is not None:
                if not messagebox.askyesno(
                    "确认",
                    "即将从迁移包恢复数据：将覆盖 data/auth.db，并可能覆盖 RAGFlow volumes。\n\n是否继续？",
                ):
                    return
                self._set_status("恢复迁移包数据…")
                self._append_log(f"[{_now_str()}] 开始恢复迁移包：{cfg.migration_dir}")
                _restore_from_migration_pack(cfg.migration_dir, cfg.install_dir, self._append_log)

            if cfg.start_ragflow_if_missing and cfg.ragflow_compose_path is not None:
                self._set_status("启动 RAGFlow（如需要）…")
                self._append_log(f"[{_now_str()}] 检查/启动 RAGFlow")
                _ensure_ragflow_started(cfg.ragflow_compose_path, log=self._append_log)
            elif cfg.restore_after_install and cfg.migration_dir is not None and cfg.ragflow_compose_path is not None:
                # If we stopped it earlier, start it back.
                self._set_status("启动 RAGFlow…")
                self._append_log(f"[{_now_str()}] 启动 RAGFlow")
                out = _compose_start(cfg.ragflow_compose_path, cwd=cfg.ragflow_compose_path.parent)
                if out:
                    self._append_log(out)

            self._start_compose(cfg)

            ip = _local_ip()
            self._set_status("部署完成")
            self._append_log(f"[{_now_str()}] 前端地址：http://{ip}:8080")
            self._append_log(f"[{_now_str()}] 后端地址：http://{ip}:8001/docs")
            messagebox.showinfo("完成", f"部署完成！\n\n前端：http://{ip}:8080\n后端：http://{ip}:8001/docs")
        except Exception as e:
            self._set_status("部署失败", ok=False)
            self._append_log(f"[{_now_str()}] ERROR: {e}")
            messagebox.showerror("部署失败", str(e))
        finally:
            self._set_busy(False)

    def _extract_zip(self, cfg: InstallConfig) -> None:
        self._set_status("正在解压 ZIP…")
        self._append_log(f"[{_now_str()}] 解压 ZIP：{cfg.zip_path}")

        target = cfg.install_dir
        if target.exists() and any(target.iterdir()):
            ok = messagebox.askyesno(
                "目录非空",
                f"安装目录不是空的：\n\n{target}\n\n继续将覆盖同名文件。是否继续？",
            )
            if not ok:
                raise RuntimeError("用户取消")

        _safe_mkdir(target)
        with zipfile.ZipFile(cfg.zip_path, "r") as zf:
            zf.extractall(target)

        self._append_log(f"[{_now_str()}] 解压完成")

    def _write_configs(self, cfg: InstallConfig) -> None:
        self._set_status("正在写入配置…")
        root = cfg.install_dir

        rag_path = root / "ragflow_config.json"
        raw = _read_ragflow_config(rag_path)
        raw["base_url"] = cfg.ragflow_base_url
        if cfg.ragflow_api_key:
            raw["api_key"] = cfg.ragflow_api_key
        rag_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._append_log(f"[{_now_str()}] 已写入：{rag_path}")

        env_path = root / "docker" / ".env"
        _safe_mkdir(env_path.parent)
        env_path.write_text(f"JWT_SECRET_KEY={cfg.jwt_secret_key}\n", encoding="utf-8")
        self._append_log(f"[{_now_str()}] 已写入：{env_path}")

    def _start_compose(self, cfg: InstallConfig) -> None:
        self._set_status("正在启动容器…")
        root = cfg.install_dir
        compose = root / "docker" / "docker-compose.yml"
        if not compose.exists():
            raise RuntimeError(f"找不到 docker/docker-compose.yml：{compose}")

        self._append_log(f"[{_now_str()}] 执行：docker compose up -d --build")
        _compose_up_build(compose, cwd=root)
        self._append_log(f"[{_now_str()}] 容器已启动")


def main() -> int:
    app = InstallerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
