param(
  [string]$SourceDbPath = "data/auth.db",
  [string]$TenantRoot = "",
  [switch]$Force,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ([System.IO.Path]::IsPathRooted($SourceDbPath)) {
  $sourceDb = $SourceDbPath
} else {
  $sourceDb = (Join-Path $repoRoot $SourceDbPath)
}
if (-not (Test-Path $sourceDb)) {
  throw "source_db_not_found: $sourceDb"
}
$sourceDb = (Resolve-Path $sourceDb).Path

if ([string]::IsNullOrWhiteSpace($TenantRoot)) {
  $TenantRoot = Join-Path ([System.IO.Path]::GetDirectoryName($sourceDb)) "tenants"
}
if (-not [System.IO.Path]::IsPathRooted($TenantRoot)) {
  $TenantRoot = Join-Path $repoRoot $TenantRoot
}

if (-not (Test-Path $TenantRoot)) {
  New-Item -Path $TenantRoot -ItemType Directory -Force | Out-Null
}

$py = @'
from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(conn, table):
        return set()
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r[1]) for r in rows}


def delete_not_in(conn: sqlite3.Connection, table: str, column: str, keep_values: list[str]) -> None:
    if not table_exists(conn, table):
        return
    if column not in table_columns(conn, table):
        return
    if not keep_values:
        conn.execute(f"DELETE FROM {table}")
        return
    placeholders = ",".join(["?"] * len(keep_values))
    conn.execute(f"DELETE FROM {table} WHERE {column} NOT IN ({placeholders})", keep_values)


def migrate_company_db(*, source_db: Path, target_db: Path, company_id: int, dry_run: bool) -> dict[str, int]:
    if not dry_run:
        target_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_db, target_db)

    db_for_work = source_db if dry_run else target_db
    conn = sqlite3.connect(str(db_for_work))
    try:
        conn.row_factory = sqlite3.Row
        user_rows = conn.execute(
            "SELECT user_id FROM users WHERE company_id = ?",
            (company_id,),
        ).fetchall()
        keep_users = [str(r["user_id"]) for r in user_rows if r["user_id"]]

        if not dry_run:
            conn.execute("DELETE FROM users WHERE company_id IS NULL OR company_id != ?", (company_id,))
            delete_not_in(conn, "user_permission_groups", "user_id", keep_users)
            delete_not_in(conn, "auth_login_sessions", "user_id", keep_users)
            delete_not_in(conn, "kb_documents", "uploaded_by", keep_users)
            delete_not_in(conn, "download_logs", "downloaded_by", keep_users)
            delete_not_in(conn, "deletion_logs", "deleted_by", keep_users)
            delete_not_in(conn, "chat_sessions", "created_by", keep_users)

            if table_exists(conn, "audit_events"):
                cols = table_columns(conn, "audit_events")
                if "company_id" in cols:
                    conn.execute("DELETE FROM audit_events WHERE company_id IS NULL OR company_id != ?", (company_id,))
                elif "actor" in cols:
                    delete_not_in(conn, "audit_events", "actor", keep_users)

            if table_exists(conn, "data_security_settings") and "auth_db_path" in table_columns(conn, "data_security_settings"):
                conn.execute("UPDATE data_security_settings SET auth_db_path = ? WHERE id = 1", (str(target_db),))

            conn.commit()

        return {
            "company_id": int(company_id),
            "users": int(len(keep_users)),
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Split single auth DB into per-company tenant DBs.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--tenant-root", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_db = Path(args.source).resolve()
    tenant_root = Path(args.tenant_root).resolve()

    if not source_db.exists():
        raise SystemExit(f"source_db_not_found: {source_db}")
    tenant_root.mkdir(parents=True, exist_ok=True)

    src = sqlite3.connect(str(source_db))
    try:
        rows = src.execute(
            "SELECT DISTINCT company_id FROM users WHERE company_id IS NOT NULL ORDER BY company_id ASC"
        ).fetchall()
        company_ids = [int(r[0]) for r in rows]
    finally:
        src.close()

    if not company_ids:
        raise SystemExit("no_company_users_found_in_source_db")

    print(f"source_db={source_db}")
    print(f"tenant_root={tenant_root}")
    print(f"companies={company_ids}")

    for cid in company_ids:
        target_db = tenant_root / f"company_{cid}" / "auth.db"
        if target_db.exists() and not args.force and not args.dry_run:
            raise SystemExit(f"target_exists_without_force: {target_db}")

        if args.force and target_db.exists() and not args.dry_run:
            target_db.unlink()

        summary = migrate_company_db(
            source_db=source_db,
            target_db=target_db,
            company_id=cid,
            dry_run=bool(args.dry_run),
        )
        print(f"company={summary['company_id']} users={summary['users']} target={target_db}")

    print("migration_done")


if __name__ == "__main__":
    main()
'@

$pythonArgs = @("-", "--source", $sourceDb, "--tenant-root", $TenantRoot)
if ($Force) { $pythonArgs += "--force" }
if ($DryRun) { $pythonArgs += "--dry-run" }

$py | python @pythonArgs
