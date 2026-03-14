#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Ensure repository root is importable when executing the script directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.database.schema.ensure import ensure_schema
from backend.database.sqlite import connect_sqlite

ROLLBACK_SCOPES: dict[str, list[str]] = {
    "w11": [
        "unified_task_events",
        "unified_task_jobs",
        "unified_tasks",
        "paper_plag_hits",
        "paper_plag_reports",
        "paper_versions",
        "egress_decision_audits",
    ],
    "full": [
        "chat_message_sources",
        "chat_sessions",
        "auth_login_sessions",
        "user_permission_groups",
        "permission_group_folders",
        "permission_groups",
        "paper_download_items",
        "paper_download_sessions",
        "patent_download_items",
        "patent_download_sessions",
        "kb_directory_dataset_bindings",
        "kb_directory_nodes",
        "unified_task_events",
        "unified_task_jobs",
        "unified_tasks",
        "paper_plag_hits",
        "paper_plag_reports",
        "paper_versions",
        "egress_decision_audits",
        "nas_import_tasks",
        "backup_jobs",
        "backup_locks",
        "data_security_settings",
        "org_directory_audit_logs",
        "departments",
        "companies",
        "audit_events",
        "deletion_logs",
        "download_logs",
        "search_configs",
        "upload_settings",
        "kb_documents",
        "users",
    ],
}


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (str(table_name or ""),),
    ).fetchone()
    return row is not None


def _snapshot_tables(conn, table_names: list[str]) -> dict[str, bool]:
    return {name: _table_exists(conn, name) for name in table_names}


def _drop_tables(conn, table_names: list[str]) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        for table_name in table_names:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _run_single_scope(db_path: Path, *, scope: str, table_names: list[str]) -> dict[str, Any]:
    ensure_schema(db_path)

    conn = connect_sqlite(db_path)
    try:
        before_rollback = _snapshot_tables(conn, table_names)
        _drop_tables(conn, table_names)
        after_rollback = _snapshot_tables(conn, table_names)
    finally:
        conn.close()

    ensure_schema(db_path)

    conn = connect_sqlite(db_path)
    try:
        after_recover = _snapshot_tables(conn, table_names)
    finally:
        conn.close()

    before_ok = all(bool(v) for v in before_rollback.values())
    rollback_ok = all(not bool(v) for v in after_rollback.values())
    recover_ok = all(bool(v) for v in after_recover.values())

    return {
        "scope": scope,
        "target_tables": list(table_names),
        "before_rollback": before_rollback,
        "after_rollback": after_rollback,
        "after_recover": after_recover,
        "before_ok": before_ok,
        "rollback_ok": rollback_ok,
        "recover_ok": recover_ok,
        "verdict": "PASS" if (before_ok and rollback_ok and recover_ok) else "FAIL",
    }


def _render_markdown_report(*, generated_at: str, db_path: str, scope_results: dict[str, dict[str, Any]], overall_verdict: str) -> str:
    lines: list[str] = [
        "# IT-MIGRATION-ROLLBACK-001 Rollback Drill Report",
        "",
        f"- Generated at: {generated_at}",
        f"- Drill database: `{db_path}`",
        f"- Scopes: {', '.join(scope_results.keys())}",
        f"- Overall verdict: **{overall_verdict}**",
        "",
    ]

    for scope_name, result in scope_results.items():
        lines.extend(
            [
                f"## Scope: {scope_name}",
                "",
                f"- Verdict: **{result.get('verdict')}**",
                f"- Target tables: {len(result.get('target_tables') or [])}",
                f"- Checks: before_ok={result.get('before_ok')} rollback_ok={result.get('rollback_ok')} recover_ok={result.get('recover_ok')}",
                "",
                "| Table | Before | AfterRollback | AfterRecover |",
                "|---|---|---|---|",
            ]
        )

        before = result.get("before_rollback") or {}
        after_drop = result.get("after_rollback") or {}
        after_recover = result.get("after_recover") or {}
        for table_name in result.get("target_tables") or []:
            lines.append(
                f"| {table_name} | {before.get(table_name)} | {after_drop.get(table_name)} | {after_recover.get(table_name)} |"
            )

        lines.append("")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run schema rollback drill for migration scopes.")
    parser.add_argument(
        "--db-path",
        default="",
        help="Path to drill sqlite db. If omitted, uses a temporary db path.",
    )
    parser.add_argument(
        "--scope",
        default="all",
        choices=["all", *sorted(ROLLBACK_SCOPES.keys())],
        help="Rollback scope to drill.",
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Keep temp drill db directory after run (only applies when --db-path is omitted).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    temp_root: Path | None = None
    if str(args.db_path or "").strip():
        db_path = Path(str(args.db_path)).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        temp_root = Path(tempfile.gettempdir()) / f"ragflowauth_schema_rollback_{uuid4().hex}"
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = temp_root / "auth.db"

    scope_names = sorted(ROLLBACK_SCOPES.keys()) if args.scope == "all" else [str(args.scope)]
    scope_results: dict[str, dict[str, Any]] = {}

    for scope_name in scope_names:
        scope_results[scope_name] = _run_single_scope(db_path, scope=scope_name, table_names=ROLLBACK_SCOPES[scope_name])

    overall_verdict = "PASS" if all((item.get("verdict") == "PASS") for item in scope_results.values()) else "FAIL"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "db_path": str(db_path),
        "scope": args.scope,
        "scopes": scope_results,
        "overall_verdict": overall_verdict,
    }

    report_dir = Path("doc/test/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_text = _render_markdown_report(
        generated_at=generated_at,
        db_path=str(db_path),
        scope_results=scope_results,
        overall_verdict=overall_verdict,
    )

    md_output = report_dir / f"schema_rollback_drill_report_{timestamp}.md"
    md_latest = report_dir / "schema_rollback_drill_report_latest.md"
    json_output = report_dir / f"schema_rollback_drill_report_{timestamp}.json"
    json_latest = report_dir / "schema_rollback_drill_report_latest.json"

    md_output.write_text(md_text, encoding="utf-8")
    md_latest.write_text(md_text, encoding="utf-8")
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json_latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ROLLBACK] overall_verdict={overall_verdict}")
    for scope_name, result in scope_results.items():
        print(f"[ROLLBACK] scope={scope_name} verdict={result.get('verdict')}")
    print(f"[ROLLBACK] report: {md_output}")
    print(f"[ROLLBACK] report: {md_latest}")
    print(f"[ROLLBACK] json:   {json_output}")
    print(f"[ROLLBACK] json:   {json_latest}")

    if temp_root is not None and not args.keep_db:
        shutil.rmtree(temp_root, ignore_errors=True)

    return 0 if overall_verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
