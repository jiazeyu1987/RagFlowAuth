#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class ProbeResult:
    name: str
    ok: bool
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error_type: str | None = None
    error_errno: int | None = None
    error_winerror: int | None = None
    error_strerror: str | None = None
    error_repr: str | None = None


def _run_probe(name: str, cmd: Sequence[str]) -> ProbeResult:
    try:
        proc = subprocess.Popen(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out, err = proc.communicate(timeout=20)
        return ProbeResult(
            name=name,
            ok=(proc.returncode == 0),
            returncode=proc.returncode,
            stdout=(out or "").strip(),
            stderr=(err or "").strip(),
        )
    except OSError as exc:
        return ProbeResult(
            name=name,
            ok=False,
            error_type=type(exc).__name__,
            error_errno=getattr(exc, "errno", None),
            error_winerror=getattr(exc, "winerror", None),
            error_strerror=getattr(exc, "strerror", None),
            error_repr=repr(exc),
        )
    except Exception as exc:  # pragma: no cover - unexpected branch
        return ProbeResult(
            name=name,
            ok=False,
            error_type=type(exc).__name__,
            error_repr=repr(exc),
        )


def _find_playwright_chrome() -> str | None:
    home = os.environ.get("LOCALAPPDATA")
    if not home:
        return None
    base = Path(home) / "ms-playwright"
    if not base.exists():
        return None

    candidates = sorted(base.glob("chromium-*/chrome-win64/chrome.exe"), reverse=True)
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _find_playwright_headless_shell() -> str | None:
    home = os.environ.get("LOCALAPPDATA")
    if not home:
        return None
    base = Path(home) / "ms-playwright"
    if not base.exists():
        return None

    candidates = sorted(base.glob("chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), reverse=True)
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe subprocess spawn issues (e.g. EPERM).")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only.",
    )
    args = parser.parse_args()

    probes: list[tuple[str, list[str]]] = []
    probes.append(("spawn cmd.exe", ["cmd.exe", "/c", "echo ok"]))

    py = sys.executable
    probes.append(("spawn current python", [py, "-c", "print('python ok')"]))

    node = shutil.which("node")
    if node:
        probes.append(("spawn node", [node, "-e", "console.log('node ok')"]))

    chrome = _find_playwright_chrome()
    if chrome:
        probes.append(("spawn playwright chromium", [chrome, "--version"]))
    headless_shell = _find_playwright_headless_shell()
    if headless_shell:
        probes.append(("spawn playwright headless shell", [headless_shell, "--version"]))

    results = [_run_probe(name, cmd) for name, cmd in probes]
    summary = {
        "platform": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cwd": os.getcwd(),
        "probe_count": len(results),
        "failed_count": len([r for r in results if not r.ok]),
        "results": [asdict(r) for r in results],
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("== Spawn Probe Summary ==")
        print(f"platform: {summary['platform']}")
        print(f"python:   {sys.executable}")
        print(f"cwd:      {os.getcwd()}")
        print("")
        for r in results:
            status = "OK" if r.ok else "FAIL"
            print(f"[{status}] {r.name}")
            if r.returncode is not None:
                print(f"  returncode: {r.returncode}")
            if r.stdout:
                print(f"  stdout: {r.stdout}")
            if r.stderr:
                print(f"  stderr: {r.stderr}")
            if r.error_type:
                print(f"  error_type: {r.error_type}")
            if r.error_errno is not None:
                print(f"  errno: {r.error_errno}")
            if r.error_winerror is not None:
                print(f"  winerror: {r.error_winerror}")
            if r.error_strerror:
                print(f"  strerror: {r.error_strerror}")
            if r.error_repr:
                print(f"  repr: {r.error_repr}")
            print("")

    return 0 if summary["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
