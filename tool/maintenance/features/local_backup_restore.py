from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tool.maintenance.core.logging_setup import log_to_file

DOCKER_HELPER_IMAGE = "alpine:3.20"
LOCAL_BACKEND_HOST = "127.0.0.1"
LOCAL_BACKEND_PORT = 8001
_TAR_SUFFIX = ".tar.gz"


@dataclass(frozen=True)
class LocalVolumeRestorePlanItem:
    archive_name: str
    backup_volume_name: str
    local_volume_name: str


@dataclass(frozen=True)
class LocalBackupRestoreResult:
    ok: bool
    message: str
    raw: str
    restored_auth_db_path: str
    restored_volume_names: list[str]
    stopped_container_names: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_local_auth_db_path() -> Path:
    return _repo_root() / "data" / "auth.db"


def _is_port_open(host: str, port: int, timeout_seconds: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        return sock.connect_ex((host, port)) == 0


def _run_command(
    argv: list[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return runner(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _normalize_output(*parts: str) -> str:
    return "\n".join(part.strip() for part in parts if str(part or "").strip()).strip()


def _backup_volume_name_from_archive(archive_name: str) -> str:
    text = str(archive_name or "").strip()
    if not text.endswith(_TAR_SUFFIX):
        return Path(text).stem
    return text[: -len(_TAR_SUFFIX)]


def _mapping_candidates(backup_volume_name: str, local_volume_names: list[str]) -> list[str]:
    if backup_volume_name in local_volume_names:
        return [backup_volume_name]

    if backup_volume_name.startswith("ragflow_compose_"):
        preferred = f"docker_{backup_volume_name[len('ragflow_compose_'):]}"
        if preferred in local_volume_names:
            return [preferred]

    if backup_volume_name.startswith("docker_"):
        preferred = f"ragflow_compose_{backup_volume_name[len('docker_'):]}"
        if preferred in local_volume_names:
            return [preferred]

    names = []
    suffixes = {backup_volume_name}
    if backup_volume_name.startswith("ragflow_compose_"):
        suffixes.add(backup_volume_name[len("ragflow_compose_") :])
    if backup_volume_name.startswith("docker_"):
        suffixes.add(backup_volume_name[len("docker_") :])
    if "_" in backup_volume_name:
        suffixes.add(backup_volume_name.split("_", 1)[1])

    for local_name in local_volume_names:
        if local_name == backup_volume_name:
            names.append(local_name)
            continue
        for suffix in suffixes:
            if suffix and (local_name == suffix or local_name.endswith(f"_{suffix}")):
                names.append(local_name)
                break

    return sorted(dict.fromkeys(names))


def build_local_volume_restore_plan(
    *,
    backup_volumes_dir: str | Path,
    local_volume_names: list[str],
) -> tuple[list[LocalVolumeRestorePlanItem], str | None]:
    volumes_dir = Path(backup_volumes_dir)
    archives = sorted(path.name for path in volumes_dir.glob(f"*{_TAR_SUFFIX}"))
    plan: list[LocalVolumeRestorePlanItem] = []

    for archive_name in archives:
        backup_volume_name = _backup_volume_name_from_archive(archive_name)
        candidates = _mapping_candidates(backup_volume_name, local_volume_names)
        if not candidates:
            return [], f"volume_mapping_missing:{backup_volume_name}"
        if len(candidates) != 1:
            return [], f"volume_mapping_ambiguous:{backup_volume_name}:{','.join(candidates)}"
        plan.append(
            LocalVolumeRestorePlanItem(
                archive_name=archive_name,
                backup_volume_name=backup_volume_name,
                local_volume_name=candidates[0],
            )
        )

    return plan, None


def _list_local_docker_volumes(
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, list[str], str]:
    completed = _run_command(["docker", "volume", "ls", "--format", "{{.Name}}"], runner=runner)
    output = _normalize_output(completed.stdout, completed.stderr)
    if completed.returncode != 0:
        return False, [], output
    names = [line.strip() for line in output.splitlines() if line.strip()]
    return True, names, output


def _containers_using_volume(
    volume_name: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, list[tuple[str, str]], str]:
    completed = _run_command(
        ["docker", "ps", "--filter", f"volume={volume_name}", "--format", "{{.ID}}\t{{.Names}}"],
        runner=runner,
    )
    output = _normalize_output(completed.stdout, completed.stderr)
    if completed.returncode != 0:
        return False, [], output
    rows: list[tuple[str, str]] = []
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        parts = text.split("\t", 1)
        container_id = parts[0].strip()
        container_name = parts[1].strip() if len(parts) > 1 else container_id
        rows.append((container_id, container_name))
    return True, rows, output


def _stop_containers(
    container_ids: list[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, str]:
    if not container_ids:
        return True, ""
    completed = _run_command(["docker", "stop", *container_ids], runner=runner)
    return completed.returncode == 0, _normalize_output(completed.stdout, completed.stderr)


def _start_containers(
    container_ids: list[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, str]:
    if not container_ids:
        return True, ""
    completed = _run_command(["docker", "start", *container_ids], runner=runner)
    return completed.returncode == 0, _normalize_output(completed.stdout, completed.stderr)


def _restore_volume_archive(
    *,
    local_volume_name: str,
    archive_name: str,
    backup_volumes_dir: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, str]:
    restore_script = (
        "rm -rf /volume_data/* /volume_data/.??* 2>/dev/null || true; "
        f"tar -xzf /backup/{archive_name} -C /volume_data"
    )
    completed = _run_command(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{local_volume_name}:/volume_data",
            "-v",
            f"{backup_volumes_dir.resolve()}:/backup:ro",
            DOCKER_HELPER_IMAGE,
            "sh",
            "-c",
            restore_script,
        ],
        runner=runner,
    )
    return completed.returncode == 0, _normalize_output(completed.stdout, completed.stderr)


def restore_downloaded_backup_to_local(
    *,
    backup_dir: str | Path,
    auth_db_target: str | Path | None = None,
    docker_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    port_probe: Callable[[str, int], bool] = _is_port_open,
) -> LocalBackupRestoreResult:
    backup_root = Path(backup_dir)
    target_auth_db = Path(auth_db_target) if auth_db_target is not None else default_local_auth_db_path()

    if not backup_root.exists() or not backup_root.is_dir():
        return LocalBackupRestoreResult(False, "backup_dir_missing", "", str(target_auth_db), [], [])

    backup_auth_db = backup_root / "auth.db"
    if not backup_auth_db.is_file():
        return LocalBackupRestoreResult(False, "backup_auth_db_missing", "", str(target_auth_db), [], [])

    if not target_auth_db.exists() or not target_auth_db.is_file():
        return LocalBackupRestoreResult(False, "local_auth_db_missing", "", str(target_auth_db), [], [])

    if port_probe(LOCAL_BACKEND_HOST, LOCAL_BACKEND_PORT):
        return LocalBackupRestoreResult(False, "local_backend_running", "", str(target_auth_db), [], [])

    backup_volumes_dir = backup_root / "volumes"
    has_volume_archives = backup_volumes_dir.is_dir() and any(backup_volumes_dir.glob(f"*{_TAR_SUFFIX}"))

    restore_plan: list[LocalVolumeRestorePlanItem] = []
    if has_volume_archives:
        if not shutil.which("docker"):
            return LocalBackupRestoreResult(False, "docker_not_found", "", str(target_auth_db), [], [])

        docker_ping = _run_command(["docker", "info", "--format", "{{.ServerVersion}}"], runner=docker_runner)
        docker_output = _normalize_output(docker_ping.stdout, docker_ping.stderr)
        if docker_ping.returncode != 0:
            return LocalBackupRestoreResult(False, "docker_unavailable", docker_output, str(target_auth_db), [], [])

        ok, local_volume_names, out = _list_local_docker_volumes(runner=docker_runner)
        if not ok:
            return LocalBackupRestoreResult(False, "docker_volume_list_failed", out, str(target_auth_db), [], [])

        restore_plan, mapping_error = build_local_volume_restore_plan(
            backup_volumes_dir=backup_volumes_dir,
            local_volume_names=local_volume_names,
        )
        if mapping_error is not None:
            return LocalBackupRestoreResult(False, mapping_error, "", str(target_auth_db), [], [])

    container_id_to_name: dict[str, str] = {}
    for item in restore_plan:
        ok, rows, out = _containers_using_volume(item.local_volume_name, runner=docker_runner)
        if not ok:
            return LocalBackupRestoreResult(
                False,
                "docker_container_query_failed",
                out,
                str(target_auth_db),
                [],
                [],
            )
        for container_id, container_name in rows:
            container_id_to_name.setdefault(container_id, container_name)

    stopped_ids = list(container_id_to_name)
    stopped_names = [container_id_to_name[item] for item in stopped_ids]

    result = LocalBackupRestoreResult(False, "restore_not_started", "", str(target_auth_db), [], [])
    try:
        if stopped_ids:
            ok, out = _stop_containers(stopped_ids, runner=docker_runner)
            if not ok:
                result = LocalBackupRestoreResult(
                    False,
                    "container_stop_failed",
                    out,
                    str(target_auth_db),
                    [],
                    stopped_names,
                )
                return result

        try:
            shutil.copy2(backup_auth_db, target_auth_db)
        except OSError as exc:
            result = LocalBackupRestoreResult(
                False,
                "local_auth_db_copy_failed",
                str(exc),
                str(target_auth_db),
                [],
                stopped_names,
            )
            return result

        restored_volume_names: list[str] = []
        for item in restore_plan:
            ok, out = _restore_volume_archive(
                local_volume_name=item.local_volume_name,
                archive_name=item.archive_name,
                backup_volumes_dir=backup_volumes_dir,
                runner=docker_runner,
            )
            if not ok:
                result = LocalBackupRestoreResult(
                    False,
                    "volume_restore_failed",
                    _normalize_output(item.archive_name, out),
                    str(target_auth_db),
                    restored_volume_names,
                    stopped_names,
                )
                return result
            restored_volume_names.append(item.local_volume_name)

        log_to_file(
            f"[LocalBackupRestore] restored auth.db -> {target_auth_db}; volumes={','.join(restored_volume_names) or 'none'}"
        )
        result = LocalBackupRestoreResult(
            True,
            "restored",
            "",
            str(target_auth_db),
            restored_volume_names,
            stopped_names,
        )
    finally:
        if stopped_ids:
            ok, out = _start_containers(stopped_ids, runner=docker_runner)
            if not ok:
                log_to_file(f"[LocalBackupRestore] container restart failed: {out}", "ERROR")
                if result.ok:
                    result = LocalBackupRestoreResult(
                        False,
                        "container_restart_failed",
                        out,
                        result.restored_auth_db_path,
                        result.restored_volume_names,
                        result.stopped_container_names,
                    )
    return result
