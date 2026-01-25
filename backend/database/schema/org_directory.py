from __future__ import annotations

import sqlite3
import time

from .helpers import table_exists


def ensure_companies_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "companies"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at_ms INTEGER NOT NULL,
            updated_at_ms INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)")


def ensure_departments_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "departments"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            department_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at_ms INTEGER NOT NULL,
            updated_at_ms INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_name ON departments(name)")


def ensure_org_directory_audit_logs_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "org_directory_audit_logs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS org_directory_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_id INTEGER,
            before_name TEXT,
            after_name TEXT,
            actor_user_id TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_type ON org_directory_audit_logs(entity_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_action ON org_directory_audit_logs(action)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_time ON org_directory_audit_logs(created_at_ms)")


def seed_default_companies(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "companies"):
        return
    cur = conn.execute("SELECT COUNT(*) FROM companies")
    row = cur.fetchone()
    if not row or row[0] != 0:
        return

    now_ms = int(time.time() * 1000)
    names = ["瑛泰医疗", "璞润医疗", "七木医疗", "璞慧医疗", "自动化所", "璞霖医疗", "其他"]
    conn.executemany(
        "INSERT OR IGNORE INTO companies (name, created_at_ms, updated_at_ms) VALUES (?, ?, ?)",
        [(n, now_ms, now_ms) for n in names],
    )


def seed_default_departments(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "departments"):
        return
    cur = conn.execute("SELECT COUNT(*) FROM departments")
    row = cur.fetchone()
    if not row or row[0] != 0:
        return

    now_ms = int(time.time() * 1000)
    names = ["技术部", "质量部", "生产部", "行政部", "总经办", "董办", "人事部", "法务部", "财务部"]
    conn.executemany(
        "INSERT OR IGNORE INTO departments (name, created_at_ms, updated_at_ms) VALUES (?, ?, ?)",
        [(n, now_ms, now_ms) for n in names],
    )

