#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_FRONTEND_BASE_URL = "http://127.0.0.1:33001"
DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:38001"
DEFAULT_REALDATA_SPECS = [
    "e2e/tests/integration.chat-agents.real-flow.spec.js",
    "e2e/tests/integration.ragflow.real-chat.multiturn.spec.js",
    "e2e/tests/integration.ragflow.real-search.matrix.spec.js",
]


def _run_and_report(*, cmd: list[str], cwd: Path, env: dict[str, str]) -> int:
    print("[RUN]", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(cwd), env=env)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Playwright real-data E2E tests.")
    parser.add_argument("--strict", action="store_true", help="Require the full real-data chain to be ready.")
    parser.add_argument("--grep", default="@realdata", help='Playwright grep pattern (default: "@realdata").')
    parser.add_argument("--workers", default="1", help="Playwright workers count (default: 1).")
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue running remaining real-data specs after a failure (default: stop on first failure).",
    )
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
    env.setdefault("E2E_FRONTEND_BASE_URL", DEFAULT_FRONTEND_BASE_URL)
    env.setdefault("E2E_BACKEND_BASE_URL", DEFAULT_BACKEND_BASE_URL)
    if args.strict:
        env["E2E_REQUIRE_REAL_FLOW"] = "1"
        env["E2E_BOOTSTRAP_REQUIRE_RAGFLOW"] = "1"

    print("[CWD]", str(fronted_dir))
    print(f"[ENV] E2E_FRONTEND_BASE_URL={env['E2E_FRONTEND_BASE_URL']}")
    print(f"[ENV] E2E_BACKEND_BASE_URL={env['E2E_BACKEND_BASE_URL']}")
    if args.strict:
        print("[ENV] E2E_REQUIRE_REAL_FLOW=1")
        print("[ENV] E2E_BOOTSTRAP_REQUIRE_RAGFLOW=1")

    if args.grep.strip() == "@realdata":
        exit_code = 0
        total_specs = len(DEFAULT_REALDATA_SPECS)
        for index, spec in enumerate(DEFAULT_REALDATA_SPECS, start=1):
            print(f"[CASE] {index}/{total_specs} {spec}")
            cmd = [npx, "playwright", "test", spec, "--workers", str(args.workers)]
            code = _run_and_report(cmd=cmd, cwd=fronted_dir, env=env)
            if code != 0:
                if exit_code == 0:
                    exit_code = code
                if not args.continue_on_failure:
                    print(f"[FAIL-FAST] stop after failure in {spec}")
                    return exit_code
        return exit_code

    cmd = [npx, "playwright", "test", "--grep", args.grep, "--workers", str(args.workers)]
    return _run_and_report(cmd=cmd, cwd=fronted_dir, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
