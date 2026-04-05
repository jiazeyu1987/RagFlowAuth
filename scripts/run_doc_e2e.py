#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

DEFAULT_FRONTEND_BASE_URL = "http://127.0.0.1:33002"
DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:38002"


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"[ERROR] Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ERROR] Manifest JSON invalid: {path}: {exc}") from exc


def normalize_scopes(raw_scopes: list[str]) -> list[str]:
    scopes = raw_scopes or ["unit", "role"]
    ordered = []
    seen = set()
    for scope in scopes:
        if scope == "all":
            for expanded in ("unit", "role"):
                if expanded not in seen:
                    ordered.append(expanded)
                    seen.add(expanded)
            continue
        if scope not in {"unit", "role"}:
            raise SystemExit(f"[ERROR] Unsupported scope: {scope}")
        if scope not in seen:
            ordered.append(scope)
            seen.add(scope)
    return ordered


def collect_entries(manifest: dict, scopes: list[str]) -> list[dict]:
    groups = manifest.get("groups")
    if not isinstance(groups, dict):
        raise SystemExit("[ERROR] Manifest missing object field: groups")

    entries: list[dict] = []
    for scope in scopes:
        group_entries = groups.get(scope)
        if not isinstance(group_entries, list):
            raise SystemExit(f"[ERROR] Manifest group is not a list: {scope}")
        for item in group_entries:
            if not isinstance(item, dict):
                raise SystemExit(f"[ERROR] Manifest entry in group {scope} is not an object")
            doc = item.get("doc")
            specs = item.get("specs")
            if not isinstance(doc, str) or not doc.strip():
                raise SystemExit(f"[ERROR] Manifest entry in group {scope} missing doc")
            if not isinstance(specs, list) or not specs or not all(isinstance(spec, str) and spec.strip() for spec in specs):
                raise SystemExit(f"[ERROR] Manifest entry for {doc} must contain a non-empty specs list")
            entries.append({"scope": scope, "doc": doc, "specs": specs})
    if not entries:
        raise SystemExit("[ERROR] No manifest entries matched the selected scope")
    return entries


def dedupe_specs(entries: list[dict]) -> list[str]:
    ordered = OrderedDict()
    for entry in entries:
        for spec in entry["specs"]:
            ordered.setdefault(spec, None)
    return list(ordered.keys())


def relative_to_fronted(spec_path: str, repo_root: Path, fronted_dir: Path) -> str:
    absolute = (repo_root / spec_path).resolve()
    return absolute.relative_to(fronted_dir.resolve()).as_posix()


def ensure_existing_specs(specs: list[str], repo_root: Path) -> list[str]:
    missing = []
    for spec in specs:
        if not (repo_root / spec).exists():
            missing.append(spec)
    if missing:
        joined = "\n".join(f"  - {item}" for item in missing)
        raise SystemExit(f"[ERROR] Manifest references missing spec files:\n{joined}")
    return specs


def build_report(
    *,
    repo_root: Path,
    manifest_path: Path,
    scopes: list[str],
    entries: list[dict],
    specs: list[str],
    runs: list[dict],
    fronted_dir: Path,
    exit_code: int,
    output: str,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall = "PASS" if exit_code == 0 else "FAIL"
    lines = [
        "# Doc E2E Report",
        "",
        f"- Time: {now}",
        f"- Repository: `{repo_root}`",
        f"- Manifest: `{manifest_path}`",
        f"- Scopes: `{', '.join(scopes)}`",
        f"- Overall: **{overall}**",
        f"- Doc Count: **{len(entries)}**",
        f"- Spec Count: **{len(specs)}**",
        "",
        "## Run Mode",
        "",
        f"- CWD: `{fronted_dir}`",
        "- Strategy: `one-spec-per-playwright-run`",
        "",
        "## Docs",
        "",
        "| Scope | Doc | Spec Count |",
        "|---|---|---:|",
    ]
    for entry in entries:
        lines.append(f"| {entry['scope']} | `{entry['doc']}` | {len(entry['specs'])} |")

    lines.extend(
        [
            "",
            "## Specs",
            "",
        ]
    )
    lines.extend([f"- `{spec}`" for spec in specs])
    lines.extend(
        [
            "",
            "## Spec Runs",
            "",
            "| Spec | Result | Command |",
            "|---|---|---|",
        ]
    )
    for run in runs:
        status = "PASS" if int(run["exit_code"]) == 0 else "FAIL"
        lines.append(f"| `{run['spec']}` | {status} | `{' '.join(run['command'])}` |")
    lines.extend(
        [
            "",
            "## Raw Output",
            "",
            "```text",
            output.rstrip(),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report_dir: Path, content: str) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = report_dir / f"doc_e2e_report_{timestamp}.md"
    latest_file = report_dir / "doc_e2e_report_latest.md"
    output_file.write_text(content, encoding="utf-8", newline="\n")
    latest_file.write_text(content, encoding="utf-8", newline="\n")
    return output_file


def write_console_text(text: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    payload = text.encode(encoding, errors="replace")
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(payload)
        sys.stdout.flush()
        return
    sys.stdout.write(payload.decode(encoding, errors="replace"))
    sys.stdout.flush()


def run_playwright_specs(
    *,
    npx_path: str,
    fronted_dir: Path,
    env: dict[str, str],
    playwright_specs: list[str],
    workers: int,
) -> tuple[int, list[dict], str]:
    combined_output_parts: list[str] = []
    runs: list[dict] = []
    final_exit_code = 0

    for spec in playwright_specs:
        command = [
            npx_path,
            "playwright",
            "test",
            "--config",
            "playwright.docs.config.js",
            spec,
            f"--workers={workers}",
        ]
        result = subprocess.run(
            command,
            cwd=fronted_dir,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        runs.append(
            {
                "spec": spec,
                "command": command,
                "exit_code": result.returncode,
            }
        )
        combined_output_parts.append(
            "\n".join(
                [
                    f"$ {' '.join(command)}",
                    result.stdout.rstrip(),
                ]
            ).rstrip()
        )
        if result.returncode != 0 and final_exit_code == 0:
            final_exit_code = result.returncode

    return final_exit_code, runs, "\n\n".join(part for part in combined_output_parts if part)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run doc/e2e-aligned Playwright specs against the full real chain.")
    parser.add_argument("--repo-root", help="Repository root. Defaults to the parent of this script.")
    parser.add_argument("--manifest", help="Manifest path. Defaults to doc/e2e/manifest.json under the repo root.")
    parser.add_argument("--fronted-dir", help="Frontend directory. Defaults to <repo-root>/fronted.")
    parser.add_argument("--scope", action="append", choices=["all", "unit", "role"], help="Restrict to one or more scopes.")
    parser.add_argument("--workers", type=int, default=1, help="Playwright worker count. Defaults to 1.")
    parser.add_argument("--list", action="store_true", help="List docs and specs without running Playwright.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    manifest_path = Path(args.manifest).resolve() if args.manifest else (repo_root / "doc" / "e2e" / "manifest.json")
    fronted_dir = Path(args.fronted_dir).resolve() if args.fronted_dir else (repo_root / "fronted")
    report_dir = repo_root / "doc" / "test" / "reports"
    scopes = normalize_scopes(args.scope or ["all"])

    npx_path = shutil.which("npx.cmd") or shutil.which("npx")
    if npx_path is None:
        raise SystemExit("[ERROR] `npx` is required but was not found in PATH.")
    if not fronted_dir.exists():
        raise SystemExit(f"[ERROR] Frontend directory not found: {fronted_dir}")

    manifest = load_manifest(manifest_path)
    entries = collect_entries(manifest, scopes)
    specs = ensure_existing_specs(dedupe_specs(entries), repo_root)

    if args.list:
        print(f"Scopes: {', '.join(scopes)}")
        print("Docs:")
        for entry in entries:
            print(f"- [{entry['scope']}] {entry['doc']}")
            for spec in entry["specs"]:
                print(f"  - {spec}")
        print("Specs:")
        for spec in specs:
            print(f"- {spec}")
        return 0

    playwright_specs = [relative_to_fronted(spec, repo_root, fronted_dir) for spec in specs]
    env = os.environ.copy()
    env.setdefault("E2E_MODE", "real")
    env.setdefault("E2E_FRONTEND_BASE_URL", DEFAULT_FRONTEND_BASE_URL)
    env.setdefault("E2E_BACKEND_BASE_URL", DEFAULT_BACKEND_BASE_URL)
    env.setdefault("E2E_TEST_DB_PATH", str(repo_root / "data" / "e2e" / "doc_auth.db"))
    env.setdefault("E2E_BOOTSTRAP_SCRIPT", str(repo_root / "scripts" / "bootstrap_doc_test_env.py"))
    env.setdefault("E2E_BOOTSTRAP_REQUIRE_RAGFLOW", "1")

    exit_code, runs, output = run_playwright_specs(
        npx_path=npx_path,
        fronted_dir=fronted_dir,
        env=env,
        playwright_specs=playwright_specs,
        workers=args.workers,
    )
    report = build_report(
        repo_root=repo_root,
        manifest_path=manifest_path,
        scopes=scopes,
        entries=entries,
        specs=specs,
        runs=runs,
        fronted_dir=fronted_dir,
        exit_code=exit_code,
        output=output,
    )
    report_path = write_report(report_dir, report)
    latest_path = report_dir / "doc_e2e_report_latest.md"

    write_console_text(output)
    print(f"REPORT: {report_path}")
    print(f"REPORT: {latest_path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
