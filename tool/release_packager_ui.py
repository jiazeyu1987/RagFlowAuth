# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox

APP_NAME = "发布打包工具（RagflowAuth）"
VERSION = "0.3.0"


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


def _is_ignored_path(rel_posix: str, *, include_uploads: bool) -> bool:
    rel = rel_posix.replace("\\", "/").lstrip("/")
    parts = rel.split("/")
    if not parts:
        return True

    if parts[0] in {".git", ".idea", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache"}:
        return True
    if "node_modules" in parts:
        return True
    if "__pycache__" in parts:
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
                + "。建议先在 fronted/ 里执行一次 npm install 再重新打包。"
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
    # table may or may not exist, ignore errors.
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
        if self.user_path is not None:
            return self.user_path
        if not self.expected_rel:
            return None
        p = self.expected_path(repo_root)
        return p if p.exists() else None


class PackagerApp(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1020x740")
        self.resizable(False, False)

        self.repo_root = _repo_root()
        self.output_zip_var = StringVar(value=str(self.repo_root / _default_zip_name()))

        self.include_uploads_var = BooleanVar(value=False)
        self.include_ragflow_var = BooleanVar(value=True)
        self.include_migration_var = BooleanVar(value=True)

        self.items: list[BundleItem] = [
            BundleItem(name="本项目 Docker 部署文件夹（docker/）", kind="dir", expected_rel="docker", zip_rel="docker"),
            BundleItem(name="本项目后端（backend/）", kind="dir", expected_rel="backend", zip_rel="backend"),
            BundleItem(name="本项目前端（fronted/）", kind="dir", expected_rel="fronted", zip_rel="fronted"),
            BundleItem(name="工具（tool/，含一键部署/恢复脚本）", kind="dir", expected_rel="tool", zip_rel="tool"),
            BundleItem(name="本项目数据库（data/auth.db）", kind="file", expected_rel="data/auth.db", zip_rel="data/auth.db"),
            BundleItem(name="本项目上传目录（可选 data/uploads）", kind="dir", expected_rel="data/uploads", zip_rel="data/uploads", optional=True),
            BundleItem(name="RAGFlow 连接配置（ragflow_config.json）", kind="file", expected_rel="ragflow_config.json", zip_rel="ragflow_config.json"),
            # The following two items are populated dynamically from auth.db (data security settings/jobs)
            BundleItem(name="RAGFlow compose 目录（用于新机一键启动 RAGFlow）", kind="dir", expected_rel="", zip_rel="ragflow_compose", optional=True),
            BundleItem(name="迁移包（migration_pack_...，用于恢复知识库数据）", kind="dir", expected_rel="", zip_rel="migration_pack", optional=True),
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
            text="说明：如果勾选“包含 RAGFlow/迁移包”，新电脑只需要一个 ZIP 就能部署并恢复数据。",
            fg="#555555",
        ).pack(anchor="w", pady=(4, 14))

        top = tk.Frame(container)
        top.pack(fill="x")
        tk.Label(top, text="输出 zip：", width=10, anchor="w").pack(side="left")
        tk.Entry(top, textvariable=self.output_zip_var).pack(side="left", fill="x", expand=True)
        tk.Button(top, text="选择…", width=10, command=self._pick_output).pack(side="left", padx=(8, 0))

        opts = tk.Frame(container)
        opts.pack(fill="x", pady=(10, 10))
        tk.Checkbutton(opts, text="包含 data/uploads（通常不需要）", variable=self.include_uploads_var, command=self._refresh_status).pack(
            anchor="w"
        )
        tk.Checkbutton(opts, text="包含 RAGFlow（compose 目录）", variable=self.include_ragflow_var, command=self._refresh_status).pack(
            anchor="w"
        )
        tk.Checkbutton(opts, text="包含迁移包（migration_pack_...）", variable=self.include_migration_var, command=self._refresh_status).pack(
            anchor="w"
        )

        table = tk.Frame(container, bd=1, relief="solid")
        table.pack(fill="both", expand=True, pady=(8, 0))

        header = tk.Frame(table, bg="#f9fafb")
        header.pack(fill="x")
        tk.Label(header, text="内容", width=46, anchor="w", bg="#f9fafb").grid(row=0, column=0, padx=8, pady=6, sticky="w")
        tk.Label(header, text="状态", width=14, anchor="w", bg="#f9fafb").grid(row=0, column=1, padx=8, pady=6, sticky="w")
        tk.Label(header, text="路径（自动/可选）", anchor="w", bg="#f9fafb").grid(row=0, column=2, padx=8, pady=6, sticky="w")
        tk.Label(header, text="", width=10, bg="#f9fafb").grid(row=0, column=3, padx=8, pady=6)

        body = tk.Frame(table)
        body.pack(fill="both", expand=True)

        for idx, item in enumerate(self.items):
            row = tk.Frame(body)
            row.pack(fill="x", pady=2)

            tk.Label(row, text=item.name, width=46, anchor="w").grid(row=0, column=0, padx=8, sticky="w")
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
        tk.Button(bottom, text="刷新检测", width=10, command=self._refresh_status).pack(side="left", padx=(8, 0))
        tk.Button(bottom, text="开始打包", width=10, command=self._package).pack(side="left", padx=(8, 0))

    def _auto_fill_dynamic_paths(self) -> None:
        rag_dir = _detect_ragflow_compose_dir(self.repo_root)
        mig_dir = _detect_latest_migration_pack(self.repo_root)

        for it in self.items:
            if it.zip_rel == "ragflow_compose" and rag_dir is not None:
                it.user_path = rag_dir
            if it.zip_rel == "migration_pack" and mig_dir is not None:
                it.user_path = mig_dir

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="选择输出 zip",
            defaultextension=".zip",
            initialfile=_default_zip_name(),
            filetypes=[("ZIP", "*.zip")],
        )
        if path:
            self.output_zip_var.set(path)

    def _pick_item(self, idx: int) -> None:
        item: BundleItem = self._rows[idx]["item"]
        title = f"选择：{item.name}"
        if item.kind == "dir":
            p = filedialog.askdirectory(title=title)
            if p:
                item.user_path = Path(p)
        else:
            p = filedialog.askopenfilename(title=title)
            if p:
                item.user_path = Path(p)
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

        missing: list[str] = []
        ok_count = 0

        for row in self._rows:
            item: BundleItem = row["item"]
            if self._is_skipped(item, include_uploads=include_uploads, include_ragflow=include_ragflow, include_migration=include_migration):
                row["status"].configure(text="跳过", fg="#6b7280")
                row["path_var"].set("")
                ok_count += 1
                continue

            src = item.resolved_source(self.repo_root)
            if item.user_path is not None:
                row["path_var"].set(str(item.user_path))
            elif src is not None:
                row["path_var"].set(str(src))
            else:
                row["path_var"].set("")

            if src is None:
                if item.optional:
                    row["status"].configure(text="未选择", fg="#b45309")
                    missing.append(item.name)
                else:
                    row["status"].configure(text="未找到", fg="#b91c1c")
                    missing.append(item.name)
            else:
                row["status"].configure(text="OK", fg="#0f766e")
                ok_count += 1

        if missing:
            self.summary.configure(text=f"仍有 {len(missing)} 项未准备：{', '.join(missing)}", fg="#b91c1c")
        else:
            self.summary.configure(text="检测完成：可以开始打包。", fg="#0f766e")

    def _add_file(self, zf: zipfile.ZipFile, src: Path, arc: str) -> None:
        arc = arc.replace("\\", "/").lstrip("/")
        zf.write(str(src), arcname=arc)

    def _add_dir(self, zf: zipfile.ZipFile, src_dir: Path, arc_dir: str, *, include_uploads: bool) -> int:
        count = 0
        arc_dir = arc_dir.replace("\\", "/").strip("/")
        for p in src_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(src_dir).as_posix()
            arc = f"{arc_dir}/{rel}" if arc_dir else rel
            if _is_ignored_path(arc, include_uploads=include_uploads):
                continue
            zf.write(str(p), arcname=arc)
            count += 1
        return count

    def _package(self) -> None:
        self._refresh_status()

        include_uploads = bool(self.include_uploads_var.get())
        include_ragflow = bool(self.include_ragflow_var.get())
        include_migration = bool(self.include_migration_var.get())

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

        # Validate required items (and required optional toggles)
        missing: list[str] = []
        for item in self.items:
            if self._is_skipped(item, include_uploads=include_uploads, include_ragflow=include_ragflow, include_migration=include_migration):
                continue
            src = item.resolved_source(self.repo_root)
            if src is None:
                missing.append(item.name)
        if missing:
            messagebox.showerror("缺少内容", "以下内容未准备好，请点击“选择…”指定路径：\n\n- " + "\n- ".join(missing))
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
                "下一步：把这个 zip 复制到新电脑，运行 zip 里的 tool/release_installer_ui.py 一键部署。",
            )
        except Exception as e:
            messagebox.showerror("打包失败", str(e))


def main() -> int:
    app = PackagerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
