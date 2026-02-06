from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


ExecFn = Callable[[str], tuple[bool, str]]


DEFAULT_STAGING_DIR_CANDIDATES: tuple[str, ...] = (
    # Prefer large, non-root partitions first.
    "/var/lib/docker/tmp",  # typically a dedicated docker disk (largest)
    "/mnt/replica/_tmp",  # optional: Windows share (large, but slower)
    "/home/root/_tmp",  # fallback when /home is separate
    "/tmp",  # LAST RESORT: often on rootfs (can be full)
)


@dataclass(frozen=True)
class StagingPick:
    dir: str
    avail_kb: int


class RemoteStagingManager:
    """
    Manage remote staging directories for large temporary artifacts (image tar, data tar, etc.).

    Key behaviors:
    - Prefer large, non-root partitions first.
    - Verify dir is writable.
    - Optionally enforce minimum free space for an artifact size.
    - Provide best-effort cleanup helpers for legacy /tmp artifacts.
    """

    def __init__(self, *, exec_fn: ExecFn, candidates: tuple[str, ...] = DEFAULT_STAGING_DIR_CANDIDATES, log=None):
        self._exec = exec_fn
        self._candidates = candidates
        self._log = log

    def _log_line(self, msg: str) -> None:
        if self._log:
            try:
                self._log(msg)
            except Exception:
                pass

    def _mkdir_p(self, path: str) -> None:
        self._exec(f"mkdir -p {path} 2>/dev/null || true")

    def _dir_writable(self, path: str) -> tuple[bool, str]:
        self._mkdir_p(path)
        cmd = (
            f"set -e; "
            f"t={path}/.ragflowauth_write_test_$$; "
            f"touch $t 2>/dev/null && rm -f $t && echo OK"
        )
        ok, out = self._exec(cmd)
        if ok and ("OK" in (out or "")):
            return True, "OK"
        return False, (out or "").strip() or "not_writable"

    def _available_kb(self, path: str) -> int | None:
        ok, out = self._exec(f"df -Pk {path} 2>/dev/null | tail -n 1")
        if not ok:
            return None
        parts = (out or "").strip().split()
        if len(parts) < 4:
            return None
        try:
            return int(parts[3])
        except Exception:
            return None

    @staticmethod
    def _need_kb_for_bytes(size_bytes: int) -> int:
        if size_bytes <= 0:
            return 0
        # Round up to MB, in KB.
        return int((size_bytes + 1024 * 1024 - 1) // (1024 * 1024)) * 1024

    def pick_best_dir(self) -> StagingPick:
        """
        Pick the writable candidate with the largest available space (KB).
        """
        best_dir: str | None = None
        best_avail_kb: int = -1
        for d in self._candidates:
            writable, why = self._dir_writable(d)
            if not writable:
                self._log_line(f"[STAGING] skip {d}: not writable ({why})")
                continue
            avail_kb = self._available_kb(d)
            if avail_kb is None:
                self._log_line(f"[STAGING] skip {d}: cannot read free space (df failed)")
                continue
            if avail_kb > best_avail_kb:
                best_dir = d
                best_avail_kb = avail_kb

        if not best_dir:
            raise RuntimeError("No suitable remote staging directory found (disk full or not writable).")
        if best_dir == "/tmp":
            self._log_line("[STAGING] [WARN] selected /tmp as staging dir; this is on rootfs on many servers.")
        self._log_line(f"[STAGING] selected remote staging dir: {best_dir} (avail={best_avail_kb}KB)")
        return StagingPick(dir=best_dir, avail_kb=best_avail_kb)

    def pick_dir_for_bytes(self, *, size_bytes: int) -> StagingPick:
        """
        Pick the best dir that can fit at least `size_bytes`.
        """
        need_kb = self._need_kb_for_bytes(int(size_bytes))
        best: StagingPick | None = None
        for d in self._candidates:
            writable, why = self._dir_writable(d)
            if not writable:
                self._log_line(f"[STAGING] skip {d}: not writable ({why})")
                continue
            avail_kb = self._available_kb(d)
            if avail_kb is None:
                self._log_line(f"[STAGING] skip {d}: cannot read free space (df failed)")
                continue
            if avail_kb < need_kb:
                self._log_line(f"[STAGING] skip {d}: insufficient space (need~{need_kb}KB avail={avail_kb}KB)")
                continue
            pick = StagingPick(dir=d, avail_kb=avail_kb)
            if (best is None) or (pick.avail_kb > best.avail_kb):
                best = pick

        if not best:
            raise RuntimeError(
                "No suitable remote staging directory found for artifact size "
                f"({need_kb}KB needed). Free disk space or mount /var/lib/docker or /mnt/replica."
            )
        if best.dir == "/tmp":
            self._log_line("[STAGING] [WARN] selected /tmp as staging dir; this is on rootfs on many servers.")
        self._log_line(f"[STAGING] selected remote staging dir: {best.dir} (avail={best.avail_kb}KB)")
        return best

    @staticmethod
    def join(dir_path: str, filename: str) -> str:
        return f"{dir_path.rstrip('/')}/{filename.lstrip('/')}"

    def cleanup_legacy_tmp_release_files(self) -> None:
        self._exec(
            "rm -f /tmp/ragflowauth_release_*.tar /tmp/ragflowauth-images_*.tar "
            "/tmp/volumes*.tar* /tmp/images*.tar* 2>/dev/null || true"
        )

    def cleanup_path(self, path: str) -> None:
        self._exec(f"rm -f {path} 2>/dev/null || true")

