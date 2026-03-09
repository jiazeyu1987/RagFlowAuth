#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Playwright real-data E2E tests.")
    parser.add_argument("--strict", action="store_true", help="Set E2E_REQUIRE_REAL_FLOW=1.")
    parser.add_argument("--grep", default="@realdata", help='Playwright grep pattern (default: "@realdata").')
    parser.add_argument("--workers", default="1", help="Playwright workers count (default: 1).")
    parser.add_argument(
        "--fronted-dir",
        default=str(Path(__file__).resolve().parents[1] / "fronted"),
        help="Frontend directory containing Playwright config.",
    )
    args = parser.parse_args()

    fronted_dir = Path(args.fronted_dir).resolve()
    if not fronted_dir.exists():
        print(f"[ERR] fronted dir not found: {fronted_dir}")
        return 2

    npx = shutil.which("npx")
    if not npx:
        print("[ERR] npx not found in PATH")
        return 2

    env = os.environ.copy()
    if args.strict:
        env["E2E_REQUIRE_REAL_FLOW"] = "1"

    cmd = [npx, "playwright", "test", "--grep", args.grep, "--workers", str(args.workers)]

    print("[RUN]", " ".join(cmd))
    print("[CWD]", str(fronted_dir))
    if args.strict:
        print("[ENV] E2E_REQUIRE_REAL_FLOW=1")

    completed = subprocess.run(cmd, cwd=str(fronted_dir), env=env)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

