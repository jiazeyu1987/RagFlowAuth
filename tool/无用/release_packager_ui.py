# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
import zipfile
from dataclasses import dataclass
import os
import re
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox

import tkinter as tk

APP_NAME = "发布打包工具（RagflowAuth）"
VERSION = "0.3.1"


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_zip_name() -> str:
    return f"RagflowAuth_release_{time.strftime('%Y%m%d_%H%M%S', time.localtime())}.zip"


def _norm(p: Path) -> str:
    try:
        return str(p.resolve())
    except Exception:
        return str(p)


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def _is_ignored_path(rel_posix: str, *, include_uploads: bool) -> bool:
    rel = rel_posix.replace("\\", "/").lstrip("/")
    parts = rel.split("/")
    if not parts or parts == [""]:
        return True

    if parts[0] in {".git", ".idea", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache"}:
        return True
    if "node_modules" in parts:
        return True
    if parts[0] == "fronted" and len(parts) >= 2 and parts[1] == "build":
        return True
    if parts[0] == "data" and len(parts) >= 2 and parts[1] == "uploads" and not include_uploads:
        return True
    return False


def _frontend_lock_warnings(repo_root: Path) -> list[str]:
    warnings: list[str] = []
    pkg = repo_root / "fronted" / "package.json"
    lock = repo_root / "fronted" / "package-lock.json"
    if not pkg.exists():
        warnings.append("未找到 fronted/package.json（前端依赖文件缺失）")
        return warnings
    if not lock.exists():
        warnings.append("未找到 fronted/package-lock.json（Docker 构建前端需要它）")
        return warnings

    try:
        pkg_data = json.loads(pkg.read_text(encoding="utf-8"))
        lock_data = json.loads(lock.read_text(encoding="utf-8"))
        pkg_deps = set((pkg_data.get("dependencies") or {}).keys())
        lock_root = ((lock_data.get("packages") or {}).get("") or {}).get("dependencies") or {}
        lock_deps = set(lock_root.keys())
        missing = sorted(pkg_deps - lock_deps)
        if missing:
            warnings.append(
                "fronted/package-lock.json 可能与 package.json 不同步：缺少依赖 "
                + ", ".join(missing)
                + "。建议先在 fronted/ 里执行一次 npm install 再打包。"
            )
    except Exception:
        warnings.append("无法校验 fronted/package-lock.json（文件可能损坏或不是 UTF-8 JSON）")

    return warnings


def _read_sqlite_value(db_path: Path, sql: str, params: tuple = ()) -> str | None:
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row:
            return None
        v = row[0]
        if v is None:
            return None
        return str(v)
    finally:
        conn.close()


def _detect_ragflow_compose_dir(repo_root: Path) -> Path | None:
    db_path = repo_root / "data" / "auth.db"
    try:
        path = _read_sqlite_value(db_path, "select ragflow_compose_path from data_security_settings limit 1")
        if not path:
            return None
        p = Path(path)
        if not p.is_absolute():
            p = repo_root / p
        if p.exists() and p.is_file():
            return p.parent
    except Exception:
        return None
    return None


def _detect_latest_migration_pack(repo_root: Path) -> Path | None:
    db_path = repo_root / "data" / "auth.db"
    try:
        out_dir = _read_sqlite_value(
            db_path,
            "select output_dir from backup_jobs where status='success' and output_dir is not null order by id desc limit 1",
        )
        if not out_dir:
            return None
        p = Path(out_dir)
        if not p.is_absolute():
            p = repo_root / p
        if (p / "manifest.json").exists() and (p / "auth.db").exists():
            return p
    except Exception:
        return None
    return None


def _safe_image_tar_name(image: str) -> str:
    name = image.strip()
    for ch in ["/", ":", "@", "\\"]:
        name = name.replace(ch, "_")
    name = "".join(c for c in name if c.isalnum() or c in {"-", "_", "."}).strip("._-")
    if not name:
        name = "image"
    return f"{name}.tar"


def _ragflow_images_dir(migration_pack_dir: Path) -> Path:
    return migration_pack_dir / "ragflow" / "images"


def _ragflow_images_present(migration_pack_dir: Path) -> bool:
    images_dir = _ragflow_images_dir(migration_pack_dir)
    if not images_dir.exists() or not images_dir.is_dir():
        return False
    return any(p.is_file() and p.suffix.lower() == ".tar" for p in images_dir.iterdir())


def _list_ragflow_image_tars(migration_pack_dir: Path) -> list[Path]:
    images_dir = _ragflow_images_dir(migration_pack_dir)
    if not images_dir.exists() or not images_dir.is_dir():
        return []
    return sorted(p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() == ".tar")


def _compose_images(compose_dir: Path) -> tuple[list[str], str]:
    compose_yml = compose_dir / "docker-compose.yml"
    if not compose_yml.exists():
        return ([], f"未找到：{compose_yml}")

    # Prefer docker compose's own image resolution (includes extends, profiles, env interpolation).
    # Some upstream RAGFlow compose variants fail strict validation on certain Docker versions;
    # in that case fall back to parsing compose YAML files directly.
    proc = _run(["docker", "compose", "-f", "docker-compose.yml", "config", "--images"], cwd=compose_dir)
    if proc.returncode == 0:
        images = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
        return (sorted(set(images)), "")

    fallback_images, fallback_err = _scan_images_from_compose_files(compose_dir)
    if fallback_err:
        msg = (proc.stderr or proc.stdout or "").strip()
        return (
            [],
            "获取镜像列表失败（docker compose 校验失败，且自动回退也失败）。\n\n"
            f"docker compose 输出：\n{msg or '未知错误'}\n\n"
            f"回退输出：\n{fallback_err}",
        )
    return (fallback_images, "")


_IMAGE_RE = re.compile(r"^\s*image\s*:\s*(.+?)\s*$", re.IGNORECASE)


def _load_dotenv(dotenv_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not dotenv_path.exists():
        return env
    for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if k:
            env[k] = v
    return env


def _substitute_env_vars(value: str, env: dict[str, str]) -> str:
    # Supports: ${VAR}, ${VAR-default}, ${VAR:-default}
    s = value

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        if ":-" in inner:
            var, default = inner.split(":-", 1)
            var = var.strip()
            default = default
            v = env.get(var) or os.environ.get(var)
            return v if v not in (None, "") else default
        if "-" in inner:
            var, default = inner.split("-", 1)
            var = var.strip()
            default = default
            v = env.get(var) or os.environ.get(var)
            return v if v is not None else default
        var = inner.strip()
        v = env.get(var) or os.environ.get(var)
        return v if v is not None else match.group(0)

    # Repeat a few times in case there are multiple placeholders.
    for _ in range(3):
        new = re.sub(r"\$\{([^}]+)\}", repl, s)
        if new == s:
            break
        s = new
    return s


def _scan_images_from_compose_files(compose_dir: Path) -> tuple[list[str], str]:
    dotenv = _load_dotenv(compose_dir / ".env")
    images: list[str] = []
    yml_files = sorted(p for p in compose_dir.iterdir() if p.is_file() and p.name.startswith("docker-compose") and p.suffix in {".yml", ".yaml"})
    if not yml_files:
        return ([], "未找到 docker-compose*.yml 文件")

    for yml in yml_files:
        for raw in yml.read_text(encoding="utf-8", errors="ignore").splitlines():
            if raw.lstrip().startswith("#"):
                continue
            m = _IMAGE_RE.match(raw)
            if not m:
                continue
            img = m.group(1).strip().strip("'").strip('"')
            if not img:
                continue
            img = _substitute_env_vars(img, dotenv)
            images.append(img)

    images = sorted(set(i for i in images if i and not i.startswith("${")))
    if not images:
        return ([], "未能从 docker-compose*.yml 提取到任何 image: 行")
    unresolved = sorted(set(i for i in images if "${" in i))
    if unresolved:
        return (
            [],
            "发现未能替换的镜像变量（请检查 compose 目录下的 .env 是否完整）：\n- " + "\n- ".join(unresolved),
        )
    return (images, "")


def _export_ragflow_images(*, compose_dir: Path, migration_pack_dir: Path) -> tuple[bool, str]:
    images, err = _compose_images(compose_dir)
    if err:
        return (False, err)
    if not images:
        return (False, "未检测到任何镜像（docker compose config --images 输出为空）")

    images_dir = _ragflow_images_dir(migration_pack_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    missing_local: list[str] = []
    for image in images:
        inspect = _run(["docker", "image", "inspect", image])
        if inspect.returncode != 0:
            missing_local.append(image)
    if missing_local:
        return (
            False,
            "本机缺少以下镜像（请先在本机成功启动一次 RAGFlow 拉取/构建镜像后再导出）：\n- "
            + "\n- ".join(missing_local),
        )

    for image in images:
        tar_path = images_dir / _safe_image_tar_name(image)
        proc = _run(["docker", "save", "-o", str(tar_path), image])
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            return (False, f"导出镜像失败：{image}\n\n{msg or '未知错误'}")

    return (True, f"已导出 {len(images)} 个镜像到：{images_dir}")


@dataclass
class BundleItem:
    name: str
    kind: str  # file|dir
    expected_rel: str
    zip_rel: str
    optional: bool = False
    user_path: Path | None = None

    def expected_path(self, repo_root: Path) -> Path:
        return repo_root / self.expected_rel

    def resolved_source(self, repo_root: Path) -> Path | None:
        if self.user_path:
            return self.user_path
        if self.expected_rel:
            p = self.expected_path(repo_root)
            if p.exists():
                return p
        return None


class PackagerApp(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.repo_root = _repo_root()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("980x600")
        self.minsize(920, 560)

        self.output_zip_var = StringVar(value=str(self.repo_root / _default_zip_name()))
        self.include_uploads_var = BooleanVar(value=False)
        self.include_ragflow_var = BooleanVar(value=True)
        self.include_migration_var = BooleanVar(value=True)
        self.export_ragflow_images_var = BooleanVar(value=True)

        self.items = [
            BundleItem(name="后端代码（backend）", kind="dir", expected_rel="backend", zip_rel="backend"),
            BundleItem(name="前端代码（fronted）", kind="dir", expected_rel="fronted", zip_rel="fronted"),
            BundleItem(name="部署文件（docker）", kind="dir", expected_rel="docker", zip_rel="docker"),
            BundleItem(name="工具（tool）", kind="dir", expected_rel="tool", zip_rel="tool"),
            BundleItem(name="配置（ragflow_config.json）", kind="file", expected_rel="ragflow_config.json", zip_rel="ragflow_config.json"),
            BundleItem(name="本项目数据库（data/auth.db）", kind="file", expected_rel="data/auth.db", zip_rel="data/auth.db"),
            BundleItem(name="上传目录（可选：data/uploads）", kind="dir", expected_rel="data/uploads", zip_rel="data/uploads", optional=True),
            BundleItem(name="RAGFlow compose 目录（可选）", kind="dir", expected_rel="", zip_rel="ragflow_compose", optional=True),
            BundleItem(name="迁移包 migration_pack_...（可选）", kind="dir", expected_rel="", zip_rel="migration_pack", optional=True),
        ]

        self._rows: list[dict] = []
        self._build_ui()
        self._auto_fill_dynamic_paths()
        self._refresh_status()

    def _build_ui(self) -> None:
        pad = 12
        container = tk.Frame(self, padx=pad, pady=pad)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="一键打包：发布 ZIP（前端+后端+RAGFlow+数据）", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(
            container,
            text="说明：建议勾选“包含迁移包”和“导出 RAGFlow 镜像”，这样服务器不需要访问 Docker Hub 也能部署。",
            fg="#555555",
        ).pack(anchor="w", pady=(4, 14))

        top = tk.Frame(container)
        top.pack(fill="x")
        tk.Label(top, text="输出 zip", width=10, anchor="w").pack(side="left")
        tk.Entry(top, textvariable=self.output_zip_var).pack(side="left", fill="x", expand=True)
        tk.Button(top, text="选择…", width=10, command=self._pick_output).pack(side="left", padx=(8, 0))

        opts = tk.Frame(container)
        opts.pack(fill="x", pady=(10, 10))
        tk.Checkbutton(opts, text="包含 data/uploads（通常不需要）", variable=self.include_uploads_var, command=self._refresh_status).pack(anchor="w")
        tk.Checkbutton(opts, text="包含 RAGFlow（compose 目录）", variable=self.include_ragflow_var, command=self._refresh_status).pack(anchor="w")
        tk.Checkbutton(opts, text="包含迁移包（migration_pack_...）", variable=self.include_migration_var, command=self._refresh_status).pack(anchor="w")
        tk.Checkbutton(
            opts,
            text="导出 RAGFlow 镜像到迁移包（生成 ragflow/images/*.tar，用于离线部署）",
            variable=self.export_ragflow_images_var,
            command=self._refresh_status,
        ).pack(anchor="w")

        table = tk.Frame(container, bd=1, relief="solid")
        table.pack(fill="both", expand=True, pady=(8, 0))

        header = tk.Frame(table, bg="#f9fafb")
        header.pack(fill="x")
        tk.Label(header, text="内容", width=34, anchor="w", bg="#f9fafb").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        tk.Label(header, text="状态", width=14, anchor="w", bg="#f9fafb").grid(row=0, column=1, padx=8, pady=6, sticky="w")
        tk.Label(header, text="路径（自动/可选）", anchor="w", bg="#f9fafb").grid(row=0, column=2, padx=8, pady=6, sticky="w")
        tk.Label(header, text="", width=10, bg="#f9fafb").grid(row=0, column=3, padx=8, pady=6)

        body = tk.Frame(table)
        body.pack(fill="both", expand=True)

        for idx, item in enumerate(self.items):
            row = tk.Frame(body)
            row.pack(fill="x", pady=2)

            tk.Label(row, text=item.name, width=34, anchor="w").grid(row=0, column=0, padx=8, sticky="w")
            status = tk.Label(row, text="-", width=14, anchor="w")
            status.grid(row=0, column=1, padx=8, sticky="w")

            path_var = StringVar(value="")
            entry = tk.Entry(row, textvariable=path_var, state="readonly")
            entry.grid(row=0, column=2, padx=8, sticky="ew")
            row.grid_columnconfigure(2, weight=1)

            pick_btn = tk.Button(row, text="选择…", width=10, command=lambda i=idx: self._pick_item(i))
            pick_btn.grid(row=0, column=3, padx=8)

            self._rows.append({"item": item, "status": status, "path_var": path_var, "entry": entry, "pick": pick_btn})

        bottom = tk.Frame(container)
        bottom.pack(fill="x", pady=(12, 0))
        self.summary = tk.Label(bottom, text="", anchor="w")
        self.summary.pack(side="left", fill="x", expand=True)
        tk.Button(bottom, text="刷新检查", width=10, command=self._refresh_status).pack(side="left", padx=(8, 0))
        tk.Button(bottom, text="开始打包", width=10, command=self._package).pack(side="left", padx=(8, 0))

    def _auto_fill_dynamic_paths(self) -> None:
        ragflow_dir = _detect_ragflow_compose_dir(self.repo_root)
        migration_dir = _detect_latest_migration_pack(self.repo_root)
        for row in self._rows:
            item: BundleItem = row["item"]
            if item.zip_rel == "ragflow_compose" and ragflow_dir:
                item.user_path = ragflow_dir
            if item.zip_rel == "migration_pack" and migration_dir:
                item.user_path = migration_dir

    def _pick_output(self) -> None:
        default = Path(self.output_zip_var.get() or "").expanduser()
        initial_dir = str(default.parent) if default.parent.exists() else str(self.repo_root)
        path = filedialog.asksaveasfilename(
            title="选择输出 ZIP",
            initialdir=initial_dir,
            initialfile=default.name,
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")],
        )
        if path:
            self.output_zip_var.set(path)
        self._refresh_status()

    def _pick_item(self, idx: int) -> None:
        item = self.items[idx]
        if item.kind == "file":
            path = filedialog.askopenfilename(title=f"选择：{item.name}")
            if path:
                item.user_path = Path(path)
        else:
            path = filedialog.askdirectory(title=f"选择：{item.name}")
            if path:
                item.user_path = Path(path)
        self._refresh_status()

    def _is_skipped(self, item: BundleItem, *, include_uploads: bool, include_ragflow: bool, include_migration: bool) -> bool:
        if item.zip_rel == "data/uploads" and not include_uploads:
            return True
        if item.zip_rel == "ragflow_compose" and not include_ragflow:
            return True
        if item.zip_rel == "migration_pack" and not include_migration:
            return True
        return False

    def _refresh_status(self) -> None:
        include_uploads = bool(self.include_uploads_var.get())
        include_ragflow = bool(self.include_ragflow_var.get())
        include_migration = bool(self.include_migration_var.get())
        export_images = bool(self.export_ragflow_images_var.get())

        ok_count = 0
        need_count = 0

        for row in self._rows:
            item: BundleItem = row["item"]
            status: tk.Label = row["status"]
            path_var: StringVar = row["path_var"]

            if self._is_skipped(item, include_uploads=include_uploads, include_ragflow=include_ragflow, include_migration=include_migration):
                status.configure(text="跳过", fg="#6b7280")
                path_var.set("")
                continue

            need_count += 1
            src = item.resolved_source(self.repo_root)
            if src and src.exists():
                ok_count += 1
                status.configure(text="就绪", fg="#16a34a")
                path_var.set(_norm(src))
            else:
                status.configure(text="缺失", fg="#dc2626")
                path_var.set("")

        extra = ""
        if include_migration and export_images:
            migration_item = next((it for it in self.items if it.zip_rel == "migration_pack"), None)
            migration_dir = migration_item.resolved_source(self.repo_root) if migration_item else None
            if migration_dir and migration_dir.exists() and migration_dir.is_dir() and not _ragflow_images_present(migration_dir):
                extra = "（迁移包未含镜像：打包时可自动导出）"

        self.summary.configure(text=f"就绪：{ok_count}/{need_count}  {extra}".strip())

    def _add_file(self, zf: zipfile.ZipFile, src: Path, zip_rel: str) -> None:
        zf.write(src, arcname=zip_rel.replace("\\", "/"))

    def _add_dir(self, zf: zipfile.ZipFile, src_dir: Path, zip_rel_dir: str, *, include_uploads: bool) -> int:
        count = 0
        base = src_dir
        for p in base.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(base).as_posix()
            if _is_ignored_path(f"{zip_rel_dir}/{rel}", include_uploads=include_uploads):
                continue
            zf.write(p, arcname=f"{zip_rel_dir}/{rel}")
            count += 1
        return count

    def _package(self) -> None:
        self._refresh_status()

        include_uploads = bool(self.include_uploads_var.get())
        include_ragflow = bool(self.include_ragflow_var.get())
        include_migration = bool(self.include_migration_var.get())
        export_images = bool(self.export_ragflow_images_var.get())

        warnings = _frontend_lock_warnings(self.repo_root)
        if warnings:
            ok = messagebox.askyesno("提示", "发现可能影响 Docker 部署的问题：\n\n- " + "\n- ".join(warnings) + "\n\n仍要继续打包吗？")
            if not ok:
                return

        out = Path(self.output_zip_var.get() or "").expanduser()
        if not out.name.lower().endswith(".zip"):
            out = out.with_suffix(".zip")
        if not out.parent.exists():
            messagebox.showerror("错误", "输出目录不存在，请重新选择输出 zip。")
            return

        missing: list[str] = []
        for item in self.items:
            if self._is_skipped(item, include_uploads=include_uploads, include_ragflow=include_ragflow, include_migration=include_migration):
                continue
            src = item.resolved_source(self.repo_root)
            if src is None or not src.exists():
                missing.append(item.name)
        if missing:
            messagebox.showerror("缺少内容", "以下内容未准备好，请点击“选择…”指定路径：\n\n- " + "\n- ".join(missing))
            return

        if include_migration and export_images:
            migration_item = next((it for it in self.items if it.zip_rel == "migration_pack"), None)
            ragflow_item = next((it for it in self.items if it.zip_rel == "ragflow_compose"), None)
            migration_dir = migration_item.resolved_source(self.repo_root) if migration_item else None
            ragflow_dir = ragflow_item.resolved_source(self.repo_root) if ragflow_item else None

            if migration_dir and migration_dir.exists() and migration_dir.is_dir() and not _ragflow_images_present(migration_dir):
                ok = messagebox.askyesno(
                    "导出镜像",
                    "检测到迁移包里没有 ragflow/images/*.tar。\n\n是否现在导出 RAGFlow 镜像到迁移包？\n"
                    "（需要本机已能运行 RAGFlow，可能耗时几分钟，文件可能较大）",
                )
                if ok:
                    compose_dir = ragflow_dir if (ragflow_dir and ragflow_dir.exists()) else _detect_ragflow_compose_dir(self.repo_root)
                    if not compose_dir:
                        messagebox.showerror(
                            "导出失败",
                            "未找到 RAGFlow compose 目录。\n\n请先勾选“包含 RAGFlow（compose 目录）”并指定路径，或在系统里保存 ragflow_compose_path 后再试。",
                        )
                        return
                    success, msg = _export_ragflow_images(compose_dir=compose_dir, migration_pack_dir=migration_dir)
                    if not success:
                        messagebox.showerror("导出失败", msg)
                        return
                    messagebox.showinfo("导出完成", msg)

            # Final check (helps users confirm where the tar files are).
            if migration_dir and migration_dir.exists() and migration_dir.is_dir():
                tars = _list_ragflow_image_tars(migration_dir)
                if not tars:
                    ok = messagebox.askyesno(
                        "提示：未找到镜像文件",
                        "你勾选了“导出 RAGFlow 镜像”，但迁移包里仍未发现 ragflow/images/*.tar。\n\n"
                        "这通常表示：\n"
                        "1) 你点了“否”（未导出），或\n"
                        "2) 本机缺少镜像（没有成功启动过 RAGFlow），或\n"
                        "3) 迁移包目录选错了。\n\n"
                        "仍要继续打包吗？（继续打包后，服务器仍可能需要联网拉取镜像）",
                    )
                    if not ok:
                        return

        if out.exists():
            ok = messagebox.askyesno("覆盖确认", f"zip 已存在，是否覆盖？\n\n{out}")
            if not ok:
                return
            try:
                out.unlink()
            except Exception as e:
                messagebox.showerror("错误", f"无法覆盖该文件：{e}")
                return

        try:
            file_count = 0
            ragflow_image_tars: list[dict] = []
            if include_migration:
                migration_item = next((it for it in self.items if it.zip_rel == "migration_pack"), None)
                migration_dir = migration_item.resolved_source(self.repo_root) if migration_item else None
                if migration_dir and migration_dir.exists() and migration_dir.is_dir():
                    ragflow_image_tars = [
                        {
                            "file": p.name,
                            "size_bytes": p.stat().st_size,
                        }
                        for p in _list_ragflow_image_tars(migration_dir)
                    ]
            with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for item in self.items:
                    if self._is_skipped(
                        item,
                        include_uploads=include_uploads,
                        include_ragflow=include_ragflow,
                        include_migration=include_migration,
                    ):
                        continue
                    src = item.resolved_source(self.repo_root)
                    if src is None:
                        continue
                    if item.kind == "file":
                        self._add_file(zf, src, item.zip_rel)
                        file_count += 1
                    else:
                        file_count += self._add_dir(zf, src, item.zip_rel, include_uploads=include_uploads)

                manifest = {
                    "app": APP_NAME,
                    "version": VERSION,
                    "created_at": _now_str(),
                    "repo_root": _norm(self.repo_root),
                    "include_uploads": include_uploads,
                    "include_ragflow_compose": include_ragflow,
                    "include_migration_pack": include_migration,
                    "export_ragflow_images": export_images and include_migration,
                    "ragflow_image_tars": ragflow_image_tars,
                    "items": [
                        {
                            "name": it.name,
                            "zip_rel": it.zip_rel,
                            "source": _norm(it.resolved_source(self.repo_root)) if it.resolved_source(self.repo_root) else None,
                        }
                        for it in self.items
                        if not self._is_skipped(
                            it,
                            include_uploads=include_uploads,
                            include_ragflow=include_ragflow,
                            include_migration=include_migration,
                        )
                    ],
                }
                zf.writestr("bundle_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

            messagebox.showinfo(
                "打包完成",
                "已生成发布包：\n\n"
                f"{out}\n\n"
                f"包含文件数：{file_count}\n\n"
                "下一步：把这个 zip 复制到服务器/新电脑，运行 zip 里的 tool/release_installer_ui.py 一键部署。",
            )
        except Exception as e:
            messagebox.showerror("打包失败", str(e))


def main() -> int:
    app = PackagerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
