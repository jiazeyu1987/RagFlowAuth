from tool.maintenance.core.constants import DEFAULT_LOCAL_BACKUP_DIR


def resolve_pack_dir(*, pack_dir, path_cls, feature_list_local_backups, ui_log):
    if pack_dir is None:
        root_dir = path_cls(DEFAULT_LOCAL_BACKUP_DIR)
        entries = feature_list_local_backups(root_dir)
        if not entries:
            raise RuntimeError(f"未找到可用备份（需要包含 auth.db）：{root_dir}")
        pack_dir = entries[0].path

    ui_log(f"[SYNC] 选择备份: {pack_dir}")
    return pack_dir


def ensure_backup_payload(*, pack_dir, ui_log):
    auth_db = pack_dir / "auth.db"
    if not auth_db.exists():
        raise RuntimeError(f"备份缺少 auth.db: {pack_dir}")

    volumes_dir = pack_dir / "volumes"
    has_volumes = volumes_dir.exists() and volumes_dir.is_dir()
    if not has_volumes:
        ui_log("[SYNC] [WARN] 备份中未发现 volumes 目录，将只同步 auth.db（不包含 RAGFlow 数据）")
    return auth_db, volumes_dir, has_volumes


def build_ssh_exec(*, ssh_executor_cls, test_server_ip):
    ssh = ssh_executor_cls(test_server_ip, "root")

    def ssh_exec(cmd: str) -> tuple[bool, str]:
        ok, out = ssh.execute(cmd)
        return ok, out or ""

    return ssh, ssh_exec


def ensure_test_base_url(*, ssh_exec, test_server_ip, ui_log):
    # 0) Ensure TEST base_url points to TEST (defensive; avoid TEST reading PROD).
    cfg_path = "/opt/ragflowauth/ragflow_config.json"
    desired = f"http://{test_server_ip}:9380"
    ok, out = ssh_exec(
        f"test -f {cfg_path} || (echo MISSING && exit 0); "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    base_url = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    ui_log(f"[SYNC] [PRECHECK] TEST base_url: {base_url or '(empty)'}")
    if ok and base_url and (desired not in base_url):
        ui_log(f"[SYNC] [PRECHECK] 修正 TEST base_url -> {desired}")
        fix_cmd = (
            "set -e; "
            f"cp -f {cfg_path} {cfg_path}.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true; "
            "tmp=$(mktemp); "
            f"sed -E 's#(\"base_url\"[[:space:]]*:[[:space:]]*\")([^\\\"]+)(\")#\\1{desired}\\3#' {cfg_path} > $tmp; "
            f"mv -f $tmp {cfg_path}; "
            f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
        )
        ok2, out2 = ssh_exec(fix_cmd)
        new_val = (out2 or "").strip().splitlines()[-1].strip() if (out2 or "").strip() else ""
        ui_log(f"[SYNC] [PRECHECK] TEST base_url after: {new_val or '(empty)'}")
        if (not ok2) or (desired not in new_val):
            raise RuntimeError(f"无法修正 TEST base_url。输出: {out2}")
