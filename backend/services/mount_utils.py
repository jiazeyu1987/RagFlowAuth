from __future__ import annotations

from pathlib import Path


def normalize_posix_path(path_text: str) -> str:
    raw = str(path_text or "").strip()
    if not raw:
        return "/"
    s = raw.replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    if not s.startswith("/"):
        s = "/" + s
    if len(s) > 1:
        s = s.rstrip("/")
    return s or "/"


def read_proc_mounts() -> str:
    return Path("/proc/mounts").read_text(encoding="utf-8", errors="ignore")


def mount_fstype(mountpoint: str, *, mounts_text: str | None = None) -> str | None:
    """
    Best-effort mount fs-type detection from /proc/mounts.

    This function intentionally avoids touching the mountpoint path itself, so it
    remains safe even when the backing network storage is unhealthy.
    """
    mp = normalize_posix_path(mountpoint)
    try:
        data = mounts_text if mounts_text is not None else read_proc_mounts()
    except Exception:
        return None

    best: tuple[str, str] | None = None  # (mountpoint, fstype)
    for line in data.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mnt = normalize_posix_path(parts[1])
        fstype = str(parts[2] or "").strip().lower()
        if mnt == mp or mp.startswith(mnt + "/"):
            if best is None or len(mnt) > len(best[0]):
                best = (mnt, fstype)
    return best[1] if best else None


def is_cifs_mounted(mountpoint: str, *, mounts_text: str | None = None) -> bool:
    return mount_fstype(mountpoint, mounts_text=mounts_text) == "cifs"

