from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, TOP, X, StringVar, Tk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter.simpledialog import askstring
from tkinter.ttk import Button, Checkbutton, Entry, Frame, Label, Separator


APP_TITLE = "RagflowAuth 迁移打包工具（本项目DB + RAGFlow）"
CONFIG_FILENAME = "backup_ui_config.json"

PACKAGE_PREFIX = "migration_pack_"


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _repo_root_from_script() -> Path:
    here = Path(__file__).resolve().parent
    if (here / "backend").is_dir():
        return here
    cwd = Path.cwd()
    if (cwd / "backend").is_dir():
        return cwd
    return here


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _docker_ok() -> tuple[bool, str]:
    code, out = _run(["docker", "version"])
    if code != 0:
        return False, out or "docker 命令不可用"
    code, out = _run(["docker", "compose", "version"])
    if code != 0:
        return False, out or "docker compose 命令不可用"
    return True, ""


def _sqlite_online_backup(src_db: Path, dest_db: Path) -> None:
    _ensure_dir(dest_db.parent)
    src = sqlite3.connect(str(src_db))
    try:
        try:
            src.execute("PRAGMA wal_checkpoint(FULL)")
        except sqlite3.OperationalError:
            pass
        dst = sqlite3.connect(str(dest_db))
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()


def _docker_compose_stop(compose_file: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "stop"])
    if code != 0:
        raise RuntimeError(f"停止 RAGFlow 服务失败：{out}")


def _docker_compose_start(compose_file: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "start"])
    if code != 0:
        raise RuntimeError(f"启动 RAGFlow 服务失败：{out}")


def _list_docker_volumes_by_prefix(prefix: str) -> list[str]:
    code, out = _run(["docker", "volume", "ls", "--format", "{{.Name}}"])
    if code != 0:
        raise RuntimeError(f"无法读取 Docker volumes：{out}")
    vols: list[str] = []
    for line in (out or "").splitlines():
        name = line.strip()
        if name.startswith(prefix):
            vols.append(name)
    return sorted(vols)


def _docker_tar_volume(volume_name: str, dest_tar_gz: Path) -> None:
    _ensure_dir(dest_tar_gz.parent)
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/data:ro",
        "-v",
        f"{str(dest_tar_gz.parent)}:/backup",
        "alpine",
        "sh",
        "-lc",
        f"tar -czf /backup/{dest_tar_gz.name} -C /data .",
    ]
    code, out = _run(cmd)
    if code != 0:
        raise RuntimeError(f"备份 volume 失败：{volume_name}\n{out}")


def _autodetect_ragflow_compose(repo_root: Path) -> Path | None:
    candidates = [
        repo_root / "ragflow" / "docker-compose.yml",
        repo_root / "ragflow" / "docker-compose.yaml",
        repo_root / "docker-compose.yml",
        repo_root / "docker-compose.yaml",
        repo_root.parent / "ragflow" / "docker-compose.yml",
        repo_root.parent / "ragflow" / "docker-compose.yaml",
        repo_root.parent / "docker-compose.yml",
        repo_root.parent / "docker-compose.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


@dataclass
class UiConfig:
    target_dir: str = str((_repo_root_from_script() / "migration_packs").resolve())
    target_pc_ip: str = ""
    target_share_name: str = "backup"
    target_share_subdir: str = "RagflowAuth"
    ragflow_compose_file: str = ""
    ragflow_project_name: str = ""
    stop_ragflow_services: bool = False


class MigrationPackUi:
    def __init__(self) -> None:
        self.repo_root = _repo_root_from_script()
        self.config_path = self.repo_root / CONFIG_FILENAME

        self.root = Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("860x620")

        self.target_dir = StringVar(value=str((self.repo_root / "migration_packs").resolve()))
        self.use_remote = StringVar(value="0")
        self.target_pc_ip = StringVar(value="")
        self.target_share_name = StringVar(value="backup")
        self.target_share_subdir = StringVar(value="RagflowAuth")
        self.stop_ragflow_services = StringVar(value="0")

        self.compose_path = StringVar(value="")

        self._build()
        self._load_config_if_exists()

    def log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.logbox.insert(END, f"[{ts}] {msg}\n")
        self.logbox.see(END)

    def _build(self) -> None:
        top = Frame(self.root, padding=12)
        top.pack(side=TOP, fill=BOTH, expand=True)

        info = Frame(top)
        info.pack(side=TOP, fill=X)
        Label(info, text="项目目录：").pack(side=LEFT)
        Label(info, text=str(self.repo_root)).pack(side=LEFT)
        Button(info, text="打开目录", command=self._open_repo_root).pack(side=RIGHT)

        Separator(top).pack(side=TOP, fill=X, pady=10)

        tgt = Frame(top)
        tgt.pack(side=TOP, fill=X)
        Label(tgt, text="迁移包输出：").pack(side=LEFT)
        Checkbutton(
            tgt,
            text="输出到另一台电脑（共享目录）",
            variable=self.use_remote,
            onvalue="1",
            offvalue="0",
            command=self._sync_target_mode_ui,
        ).pack(side=LEFT, padx=8)

        self.local_target_row = Frame(top)
        self.local_target_row.pack(side=TOP, fill=X, pady=4)
        Label(self.local_target_row, text="本地文件夹：").pack(side=LEFT)
        Entry(self.local_target_row, textvariable=self.target_dir, width=60).pack(side=LEFT, padx=6)
        Button(self.local_target_row, text="选择...", command=self._choose_target_dir).pack(side=LEFT)

        self.remote_target_row = Frame(top)
        self.remote_target_row.pack(side=TOP, fill=X, pady=4)
        Label(self.remote_target_row, text="目标电脑IP：").pack(side=LEFT)
        Entry(self.remote_target_row, textvariable=self.target_pc_ip, width=18).pack(side=LEFT, padx=6)
        Label(self.remote_target_row, text="共享名：").pack(side=LEFT)
        Entry(self.remote_target_row, textvariable=self.target_share_name, width=16).pack(side=LEFT, padx=6)
        Label(self.remote_target_row, text="子目录：").pack(side=LEFT)
        Entry(self.remote_target_row, textvariable=self.target_share_subdir, width=20).pack(side=LEFT, padx=6)

        self.remote_path_row = Frame(top)
        self.remote_path_row.pack(side=TOP, fill=X, pady=2)
        Label(self.remote_path_row, text="实际路径：").pack(side=LEFT)
        self.remote_path_value = Label(self.remote_path_row, text="", foreground="#374151")
        self.remote_path_value.pack(side=LEFT, padx=6)

        opt = Frame(top)
        opt.pack(side=TOP, fill=X, pady=8)
        Checkbutton(
            opt,
            text="备份前停止 RAGFlow 服务（更一致，短暂停机）",
            variable=self.stop_ragflow_services,
            onvalue="1",
            offvalue="0",
        ).pack(side=LEFT)

        Separator(top).pack(side=TOP, fill=X, pady=10)

        rag = Frame(top)
        rag.pack(side=TOP, fill=X)
        Label(rag, text="RAGFlow docker-compose.yml：").pack(side=LEFT)
        Entry(rag, textvariable=self.compose_path, width=58).pack(side=LEFT, padx=6)
        Button(rag, text="选择...", command=self._choose_compose_file).pack(side=LEFT)

        Separator(top).pack(side=TOP, fill=X, pady=10)

        actions = Frame(top)
        actions.pack(side=TOP, fill=X)
        Button(actions, text="保存设置", command=self._save_config).pack(side=LEFT)
        Button(actions, text="测试目标文件夹", command=self._test_target).pack(side=LEFT, padx=8)
        Button(actions, text="开始迁移打包", command=self._create_pack).pack(side=LEFT, padx=8)
        Button(actions, text="打开目标文件夹", command=self._open_target).pack(side=LEFT, padx=8)

        Separator(top).pack(side=TOP, fill=X, pady=10)

        self.logbox = ScrolledText(top, height=18)
        self.logbox.pack(side=TOP, fill=BOTH, expand=True)

        self.log("说明：本工具默认一起打包两部分：")
        self.log("1) 本项目数据库：data/auth.db")
        self.log("2) RAGFlow（Docker Compose）：自动找到 docker-compose.yml + 打包对应 Docker volumes")
        self.log("如果你不想自动查找，也可以直接点击“选择...”指定 docker-compose.yml。")
        self._sync_target_mode_ui()

    def _open_repo_root(self) -> None:
        try:
            os.startfile(str(self.repo_root))
        except Exception:
            pass

    def _choose_target_dir(self) -> None:
        path = filedialog.askdirectory(title="选择迁移包输出文件夹", initialdir=str(self.repo_root))
        if path:
            self.target_dir.set(path)

    def _choose_compose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 RAGFlow docker-compose.yml",
            initialdir=str(self.repo_root),
            filetypes=[("Compose", "*.yml *.yaml"), ("All", "*.*")],
        )
        if path:
            self.compose_path.set(path)

    def _sync_target_mode_ui(self) -> None:
        use_remote = self.use_remote.get() == "1"
        if use_remote:
            self.local_target_row.pack_forget()
            self.remote_target_row.pack(side=TOP, fill=X, pady=4)
            self.remote_path_row.pack(side=TOP, fill=X, pady=2)
        else:
            self.remote_target_row.pack_forget()
            self.remote_path_row.pack_forget()
            self.local_target_row.pack(side=TOP, fill=X, pady=4)
        self._update_remote_path_preview()

    def _target_dir_resolved(self) -> Path:
        if self.use_remote.get() == "1":
            unc = _build_unc(self.target_pc_ip.get(), self.target_share_name.get(), self.target_share_subdir.get())
            return Path(unc)
        return Path(self.target_dir.get().strip())

    def _update_remote_path_preview(self) -> None:
        if self.use_remote.get() != "1":
            return
        unc = _build_unc(self.target_pc_ip.get(), self.target_share_name.get(), self.target_share_subdir.get())
        self.remote_path_value.config(text=unc or "（请填写目标电脑IP + 共享名）")

    def _test_target(self) -> None:
        target = self._target_dir_resolved()
        if not str(target).strip():
            messagebox.showerror("目标无效", "请先选择一个目标文件夹。")
            return
        try:
            _ensure_dir(target)
            probe = target / f".probe_{_timestamp()}.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            self.log(f"[OK] 目标可写：{target}")
            messagebox.showinfo("测试成功", f"目标文件夹可写：\n{target}")
        except Exception as exc:
            self.log(f"[ERROR] 目标不可用：{target} ({exc})")
            messagebox.showerror("测试失败", f"无法写入目标文件夹：\n{target}\n\n原因：{exc}")

    def _open_target(self) -> None:
        target = self._target_dir_resolved()
        try:
            os.startfile(str(target))
        except Exception:
            messagebox.showinfo("提示", f"无法自动打开：\n{target}")

    def _disable_actions(self, disabled: bool) -> None:
        try:
            self.root.attributes("-disabled", bool(disabled))
        except Exception:
            pass

    def _load_config_if_exists(self) -> None:
        try:
            if not self.config_path.exists():
                return
            data = json.loads(self.config_path.read_text(encoding="utf-8") or "{}") or {}
            cfg = UiConfig(**data)
            if cfg.target_dir:
                self.target_dir.set(cfg.target_dir)
            if cfg.target_pc_ip:
                self.use_remote.set("1")
                self.target_pc_ip.set(cfg.target_pc_ip)
                self.target_share_name.set(cfg.target_share_name or "backup")
                self.target_share_subdir.set(cfg.target_share_subdir or "RagflowAuth")
            self.stop_ragflow_services.set("1" if cfg.stop_ragflow_services else "0")
            if cfg.ragflow_compose_file:
                self.compose_path.set(cfg.ragflow_compose_file)
        except Exception:
            # ignore
            pass

    def _save_config(self) -> None:
        try:
            # Keep only minimal settings in config; other values are auto-detected.
            ip = self.target_pc_ip.get().strip() if self.use_remote.get() == "1" else ""
            cfg = UiConfig(
                target_dir=self.target_dir.get(),
                target_pc_ip=ip,
                target_share_name=self.target_share_name.get().strip() or "backup",
                target_share_subdir=self.target_share_subdir.get().strip() or "RagflowAuth",
                ragflow_compose_file=self.compose_path.get().strip(),
                stop_ragflow_services=self.stop_ragflow_services.get() == "1",
            )
            self.config_path.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.log(f"[OK] 已保存设置：{self.config_path}")
        except Exception as exc:
            self.log(f"[ERROR] 保存设置失败：{exc}")
            messagebox.showerror("保存失败", f"{exc}")

    def _resolve_ragflow_compose(self) -> Path:
        # 1) config remembered
        picked = Path(self.compose_path.get().strip()) if self.compose_path.get().strip() else None
        if picked and picked.exists():
            return picked

        # 2) auto-detect common locations
        p = _autodetect_ragflow_compose(self.repo_root)
        if p:
            return p

        # 3) ask user once (minimal)
        messagebox.showwarning(
            "找不到 RAGFlow yml",
            "找不到 RAGFlow 的 docker-compose.yml。\n\n请在弹窗里选择它的位置。",
        )
        picked = filedialog.askopenfilename(
            title="选择 RAGFlow docker-compose.yml",
            initialdir=str(self.repo_root),
            filetypes=[("Compose", "*.yml *.yaml"), ("All", "*.*")],
        )
        if not picked:
            raise RuntimeError("找不到 RAGFlow 的 docker-compose.yml（已取消选择）")
        p = Path(picked)
        if not p.exists():
            raise RuntimeError("选择的 docker-compose.yml 不存在")

        # remember for next time
        try:
            data = {}
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8") or "{}") or {}
            data["ragflow_compose_file"] = str(p)
            data["ragflow_project_name"] = str(p.parent.name)
            self.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass

        self.compose_path.set(str(p))

        return p

    def _resolve_project_name(self, compose_file: Path) -> str:
        # Try config first, else derive from compose folder name.
        try:
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8") or "{}") or {}
                name = str(data.get("ragflow_project_name") or "").strip()
                if name:
                    return name
        except Exception:
            pass
        return compose_file.parent.name

    def _remember_project_name(self, name: str) -> None:
        try:
            data = {}
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8") or "{}") or {}
            data["ragflow_project_name"] = name
            self.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass

    def _create_pack(self) -> None:
        def worker() -> None:
            self._disable_actions(True)
            try:
                ok, why = _docker_ok()
                if not ok:
                    raise RuntimeError(f"Docker 不可用：{why}")

                target_dir = self._target_dir_resolved()
                if not str(target_dir).strip():
                    raise RuntimeError("请先选择一个目标文件夹")
                _ensure_dir(target_dir)

                pack_dir = target_dir / f"{PACKAGE_PREFIX}{_timestamp()}"
                _ensure_dir(pack_dir)
                self.log(f"[INFO] 迁移包目录：{pack_dir}")

                # 1) Our DB
                src_db = self.repo_root / "data" / "auth.db"
                if not src_db.exists():
                    raise RuntimeError(f"找不到本项目数据库：{src_db}")

                self.log(f"[INFO] 备份本项目数据库：{src_db}")
                _sqlite_online_backup(src_db, pack_dir / "auth.db")
                self.log("[OK] 本项目数据库已写入：auth.db")

                # 2) RAGFlow
                compose_file = self._resolve_ragflow_compose()
                project_name = self._resolve_project_name(compose_file)
                ragflow_dir = pack_dir / "ragflow"
                volumes_dir = ragflow_dir / "volumes"
                _ensure_dir(volumes_dir)

                # Save compose file for reference
                try:
                    (ragflow_dir / "docker-compose.yml").write_text(
                        compose_file.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                except Exception:
                    # best-effort; still proceed
                    pass

                stop = self.stop_ragflow_services.get() == "1"
                if stop:
                    self.log("[INFO] 停止 RAGFlow 服务...")
                    _docker_compose_stop(compose_file)

                try:
                    # volumes are typically named: <project>_<volume>
                    prefix = f"{project_name}_"
                    vols = _list_docker_volumes_by_prefix(prefix)
                    if not vols:
                        # Ask once for project name, then retry.
                        self.log(f"[WARN] 未找到 volumes（前缀 {prefix}）")
                        new_name = askstring(
                            "需要 Compose 项目名",
                            f"找不到以 '{prefix}' 开头的 volumes。\n\n请输入正确的 Compose 项目名（例如 compose 文件所在目录名）：",
                            initialvalue=project_name,
                        )
                        if not new_name:
                            raise RuntimeError("找不到 RAGFlow volumes（已取消输入项目名）")
                        project_name = str(new_name).strip()
                        prefix = f"{project_name}_"
                        vols = _list_docker_volumes_by_prefix(prefix)
                        if not vols:
                            raise RuntimeError(f"仍然找不到 volumes（前缀 {prefix}）")
                        self._remember_project_name(project_name)

                    self.log(f"[INFO] 发现 RAGFlow volumes：{', '.join(vols)}")
                    for v in vols:
                        name = f"{v}_{_timestamp()}.tar.gz"
                        self.log(f"[INFO] 打包 volume：{v}")
                        _docker_tar_volume(v, volumes_dir / name)
                    self.log("[OK] RAGFlow volumes 打包完成")
                finally:
                    if stop:
                        self.log("[INFO] 启动 RAGFlow 服务...")
                        _docker_compose_start(compose_file)

                manifest = {
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "contains": {"auth_db": True, "ragflow": True},
                    "auth_db": {"path": "auth.db"},
                    "ragflow": {
                        "compose_file": str(compose_file),
                        "project_name": project_name,
                        "volumes_dir": "ragflow/volumes",
                        "stop_services": stop,
                    },
                }
                (pack_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

                self.log("[OK] 迁移包生成完成")
                messagebox.showinfo("完成", f"迁移包已生成：\n{pack_dir}")
            except Exception as exc:
                self.log(f"[ERROR] 失败：{exc}")
                self.log(traceback.format_exc().rstrip())
                messagebox.showerror("失败", f"{exc}")
            finally:
                self._disable_actions(False)

        threading.Thread(target=worker, daemon=True).start()

    def run(self) -> None:
        self.target_pc_ip.trace_add("write", lambda *_: self._update_remote_path_preview())
        self.target_share_name.trace_add("write", lambda *_: self._update_remote_path_preview())
        self.target_share_subdir.trace_add("write", lambda *_: self._update_remote_path_preview())
        self.root.mainloop()


def main() -> None:
    ui = MigrationPackUi()
    ui.run()


if __name__ == "__main__":
    main()
