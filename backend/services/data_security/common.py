from __future__ import annotations

import subprocess
import time
from pathlib import Path


def timestamp() -> str:
    # Include milliseconds to avoid directory name collisions
    now = time.localtime()
    ms = int(time.time() * 1000) % 1000
    return time.strftime("%Y%m%d_%H%M%S", now) + f"_{ms:03d}"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, shell=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def run_cmd_live(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    heartbeat: callable | None = None,
    heartbeat_interval_s: float = 15.0,
    timeout_s: float | None = None,
) -> tuple[int, str]:
    """
    Run a command and periodically invoke `heartbeat()` while it's running.

    Used for long-running operations (docker save / tar) so the UI doesn't look stuck.
    """
    import os
    import selectors

    start = time.time()
    last_hb = start
    lines: list[str] = []

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
        bufsize=1,
        universal_newlines=True,
    )

    def _maybe_heartbeat() -> None:
        nonlocal last_hb
        if heartbeat is None:
            return
        now = time.time()
        if now - last_hb >= heartbeat_interval_s:
            try:
                heartbeat()
            except Exception:
                pass
            last_hb = now

    # Windows' `select.select()` only works with sockets; `selectors` can raise WinError 10038 on pipes.
    # Use a simpler communicate-with-timeout loop on Windows.
    if os.name == "nt":
        try:
            while True:
                _maybe_heartbeat()
                if timeout_s is not None and time.time() - start > timeout_s:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    lines.append("[timeout] command exceeded timeout")
                    break
                try:
                    out, _ = proc.communicate(timeout=heartbeat_interval_s)
                    if out:
                        lines.extend((out or "").splitlines())
                    break
                except subprocess.TimeoutExpired as e:
                    if getattr(e, "output", None):
                        lines.extend(str(e.output).splitlines())
                    continue
        finally:
            out = "\n".join(lines).strip()
            rc = proc.returncode if proc.returncode is not None else 1
            return int(rc), out

    sel = selectors.DefaultSelector()
    if proc.stdout is not None:
        sel.register(proc.stdout, selectors.EVENT_READ)

    try:
        while True:
            _maybe_heartbeat()

            if timeout_s is not None and time.time() - start > timeout_s:
                try:
                    proc.kill()
                except Exception:
                    pass
                lines.append("[timeout] command exceeded timeout")
                break

            if proc.poll() is not None:
                # Drain remaining output (best-effort)
                while True:
                    events = sel.select(timeout=0)
                    if not events:
                        break
                    for key, _ in events:
                        chunk = key.fileobj.readline()
                        if not chunk:
                            # EOF: avoid busy-loop on readable-at-EOF streams.
                            try:
                                sel.unregister(key.fileobj)
                            except Exception:
                                pass
                            try:
                                key.fileobj.close()
                            except Exception:
                                pass
                            continue
                        lines.append(chunk.rstrip("\n"))
                break

            events = sel.select(timeout=0.5)
            for key, _ in events:
                chunk = key.fileobj.readline()
                if not chunk:
                    # EOF: avoid busy-loop on readable-at-EOF streams.
                    try:
                        sel.unregister(key.fileobj)
                    except Exception:
                        pass
                    try:
                        key.fileobj.close()
                    except Exception:
                        pass
                    continue
                lines.append(chunk.rstrip("\n"))
                if len(lines) > 2000:
                    lines = lines[-2000:]

        try:
            proc.wait(timeout=5)
        except Exception:
            pass
    finally:
        try:
            sel.close()
        except Exception:
            pass
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except Exception:
            pass

    out = "\n".join(lines).strip()
    rc = proc.returncode if proc.returncode is not None else 1
    return int(rc), out
