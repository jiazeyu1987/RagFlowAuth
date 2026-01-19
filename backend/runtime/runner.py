from __future__ import annotations

import argparse
import logging
import sys
import time
import uuid
from pathlib import Path
from shutil import copy2, move

from backend.app.core.config import settings
from backend.app.core.paths import backend_root, repo_root, resolve_repo_path
from backend.runtime.backup import run_backup, write_default_backup_config
from backend.database.paths import resolve_auth_db_path
from backend.database.schema_migrations import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.user_store import hash_password

logger = logging.getLogger(__name__)


def resolved_paths(*, db_path: str | Path | None = None) -> dict[str, Path]:
    auth_db = resolve_auth_db_path(db_path)
    uploads_dir = resolve_repo_path(settings.UPLOAD_DIR)
    ragflow_config = repo_root() / "ragflow_config.json"
    return {
        "repo_root": repo_root(),
        "auth_db": auth_db,
        "uploads_dir": uploads_dir,
        "ragflow_config": ragflow_config,
    }


def ensure_database(*, db_path: str | Path | None = None) -> Path:
    path = resolve_auth_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_schema(str(path))
    return path


def ensure_default_admin(*, db_path: str | Path | None = None) -> None:
    db = ensure_database(db_path=db_path)
    conn = connect_sqlite(db)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] != 0:
            return

        admin_user_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)

        cursor.execute("SELECT group_id FROM permission_groups WHERE group_name = 'admin' LIMIT 1")
        row = cursor.fetchone()
        admin_group_id = row[0] if row else None

        cursor.execute(
            """
            INSERT INTO users (
                user_id, username, password_hash, email, role, group_id, status,
                created_at_ms, last_login_at_ms, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                admin_user_id,
                "admin",
                hash_password("admin123"),
                "admin@example.com",
                "admin",
                None,
                "active",
                now_ms,
                None,
                "system",
            ),
        )

        if admin_group_id is not None:
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
                VALUES (?, ?, ?)
                """,
                (admin_user_id, admin_group_id, now_ms),
            )

        conn.commit()
        print("[OK] 已创建默认管理员：admin / admin123")
    finally:
        conn.close()


def print_paths(*, db_path: str | Path | None = None) -> None:
    paths = resolved_paths(db_path=db_path)
    print("[PATHS]")
    print(f"- 项目根目录: {paths['repo_root']}")
    print(f"- 数据库:     {paths['auth_db']}")
    print(f"- 上传目录:   {paths['uploads_dir']}")
    print(f"- RAGFlow配置: {paths['ragflow_config']}")


def migrate_data_dir(*, db_path: str | Path | None = None) -> None:
    """
    One-time migration helper:
    - Move auth DB from legacy backend/data/ -> repo_root/data/
    - Move uploads from legacy backend/data/uploads -> repo_root/data/uploads
    """
    raw_db = db_path if db_path is not None else settings.DATABASE_PATH
    raw_uploads = settings.UPLOAD_DIR

    legacy_db = backend_root() / Path(raw_db)
    new_db = repo_root() / Path(raw_db)

    legacy_uploads = backend_root() / Path(raw_uploads)
    new_uploads = repo_root() / Path(raw_uploads)

    changed = False

    if legacy_db.exists() and not new_db.exists():
        new_db.parent.mkdir(parents=True, exist_ok=True)
        copy2(legacy_db, new_db)
        legacy_marker = legacy_db.with_suffix(legacy_db.suffix + ".legacy")
        try:
            move(str(legacy_db), str(legacy_marker))
        except Exception:
            # If rename fails (e.g. locked), keep original; new DB is still created.
            legacy_marker = legacy_db
        print(f"[OK] 数据库迁移完成: {legacy_marker} -> {new_db}")
        changed = True
    elif legacy_db.exists() and new_db.exists():
        print(f"[SKIP] 新数据库已存在，未迁移: {new_db}")
    elif not legacy_db.exists() and new_db.exists():
        print(f"[OK] 已使用项目根数据库: {new_db}")
    else:
        print(f"[WARN] 未找到数据库: legacy={legacy_db} new={new_db}")

    if legacy_uploads.exists() and not new_uploads.exists():
        new_uploads.parent.mkdir(parents=True, exist_ok=True)
        try:
            move(str(legacy_uploads), str(new_uploads))
            print(f"[OK] 上传目录迁移完成: {legacy_uploads} -> {new_uploads}")
        except Exception:
            print(f"[WARN] 上传目录迁移失败（请手动移动）: {legacy_uploads} -> {new_uploads}")
        changed = True
    elif legacy_uploads.exists() and new_uploads.exists():
        # Best-effort merge without overwriting.
        moved_files = 0
        new_uploads.mkdir(parents=True, exist_ok=True)
        for src in legacy_uploads.glob("*"):
            if not src.is_file():
                continue
            dst = new_uploads / src.name
            if dst.exists():
                continue
            try:
                move(str(src), str(dst))
                moved_files += 1
            except Exception:
                continue
        print(f"[OK] 上传目录合并完成: moved_files={moved_files} -> {new_uploads}")
        changed = changed or (moved_files > 0)
    elif not legacy_uploads.exists() and new_uploads.exists():
        print(f"[OK] 已使用项目根上传目录: {new_uploads}")
    else:
        print(f"[WARN] 未找到上传目录: legacy={legacy_uploads} new={new_uploads}")

    if changed:
        print_paths(db_path=db_path)


def run_server(*, host: str | None = None, port: int | None = None, reload: bool = False) -> None:
    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"缺少 uvicorn，无法启动服务: {exc}")

    uvicorn.run(
        "backend.app.main:app",
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=reload,
        log_level="info",
    )


def main(argv: list[str] | None = None) -> None:
    # Backward-compatible default: `python -m backend` starts the server.
    if argv is None and len(sys.argv) == 1:
        run_server()
        return

    parser = argparse.ArgumentParser(description="RagflowAuth 后端统一入口")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="启动后端服务")
    p_run.add_argument("--host", default=None)
    p_run.add_argument("--port", type=int, default=None)
    p_run.add_argument("--reload", action="store_true", help="开发模式：热重载")

    p_init = sub.add_parser("init-db", help="初始化数据库（含默认管理员）")
    p_init.add_argument(
        "--db-path",
        default=None,
        help="数据库路径（相对路径按项目根目录解析；默认使用 settings.DATABASE_PATH）",
    )

    p_schema = sub.add_parser("ensure-schema", help="仅确保数据库表结构（不会创建默认管理员）")
    p_schema.add_argument(
        "--db-path",
        default=None,
        help="数据库路径（相对路径按项目根目录解析；默认使用 settings.DATABASE_PATH）",
    )

    p_paths = sub.add_parser("paths", help="打印实际使用的路径（排查配置用）")
    p_paths.add_argument(
        "--db-path",
        default=None,
        help="数据库路径（相对路径按项目根目录解析；默认使用 settings.DATABASE_PATH）",
    )

    p_migrate = sub.add_parser("migrate-data-dir", help="把历史数据目录迁移到项目根 data/（一次性）")
    p_migrate.add_argument(
        "--db-path",
        default=None,
        help="数据库路径（相对路径按项目根目录解析；默认使用 settings.DATABASE_PATH）",
    )

    p_backup_init = sub.add_parser("init-backup", help="生成备份配置文件（backup_config.json）")
    p_backup_init.add_argument(
        "--path",
        default=None,
        help="备份配置文件路径（默认：项目根目录 backup_config.json）",
    )

    p_backup = sub.add_parser("backup", help="执行一次数据库备份（复制到目标目录/共享目录）")
    p_backup.add_argument(
        "--config",
        default=None,
        help="备份配置文件路径（默认：项目根目录 backup_config.json）",
    )
    p_backup.add_argument(
        "--target-dir",
        default=None,
        help="临时覆盖配置里的 target_dir（例如 \\\\IP\\share\\RagflowAuth）",
    )

    args = parser.parse_args(argv)

    if args.cmd == "run":
        run_server(host=args.host, port=args.port, reload=bool(args.reload))
        return

    if args.cmd == "init-db":
        ensure_default_admin(db_path=args.db_path)
        print_paths(db_path=args.db_path)
        return

    if args.cmd == "ensure-schema":
        ensure_database(db_path=args.db_path)
        print("[OK] 数据库结构已就绪")
        print_paths(db_path=args.db_path)
        return

    if args.cmd == "paths":
        print_paths(db_path=args.db_path)
        return

    if args.cmd == "migrate-data-dir":
        migrate_data_dir(db_path=args.db_path)
        return

    if args.cmd == "init-backup":
        path = write_default_backup_config(args.path)
        print(f"[OK] 已生成备份配置: {path}")
        print("请用记事本打开，修改 target_dir 为另一台电脑的共享目录（UNC 路径）。")
        return

    if args.cmd == "backup":
        out = run_backup(config_path=args.config, target_dir=args.target_dir)
        print(f"[OK] 备份完成: {out}")
        return

    raise SystemExit(2)
