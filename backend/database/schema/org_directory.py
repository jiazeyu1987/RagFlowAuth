from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, columns, table_exists


def ensure_companies_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "companies"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source_key TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    else:
        add_column_if_missing(conn, "companies", "source_key TEXT")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_source_key ON companies(source_key)")
    conn.execute(
        """
        UPDATE companies
        SET source_key = TRIM(name)
        WHERE source_key IS NULL AND TRIM(COALESCE(name, '')) <> ''
        """
    )


def ensure_departments_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "departments"):
        _create_departments_table(conn)
        return

    cols = columns(conn, "departments")
    required = {
        "company_id",
        "parent_department_id",
        "source_key",
        "source_department_id",
        "level_no",
        "path_name",
        "sort_order",
    }
    if required.issubset(cols):
        _create_departments_indexes(conn)
        return

    conn.execute("ALTER TABLE departments RENAME TO departments_legacy_flat")
    _create_departments_table(conn)
    conn.execute(
        """
        INSERT INTO departments (
            department_id,
            name,
            company_id,
            parent_department_id,
            source_key,
            source_department_id,
            level_no,
            path_name,
            sort_order,
            created_at_ms,
            updated_at_ms
        )
        SELECT
            department_id,
            name,
            NULL,
            NULL,
            'legacy_department:' || CAST(department_id AS TEXT),
            NULL,
            1,
            name,
            department_id,
            created_at_ms,
            updated_at_ms
        FROM departments_legacy_flat
        """
    )
    conn.execute("DROP TABLE departments_legacy_flat")


def ensure_org_employees_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "org_employees"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS org_employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                employee_no TEXT,
                department_manager_name TEXT,
                is_department_manager INTEGER NOT NULL DEFAULT 0,
                company_id INTEGER,
                department_id INTEGER,
                source_key TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE CASCADE
            )
            """
        )
    else:
        add_column_if_missing(conn, "org_employees", "employee_user_id TEXT")
        add_column_if_missing(conn, "org_employees", "name TEXT")
        add_column_if_missing(conn, "org_employees", "email TEXT")
        add_column_if_missing(conn, "org_employees", "employee_no TEXT")
        add_column_if_missing(conn, "org_employees", "department_manager_name TEXT")
        add_column_if_missing(conn, "org_employees", "is_department_manager INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "org_employees", "company_id INTEGER")
        add_column_if_missing(conn, "org_employees", "department_id INTEGER")
        add_column_if_missing(conn, "org_employees", "source_key TEXT")
        add_column_if_missing(conn, "org_employees", "sort_order INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "org_employees", "created_at_ms INTEGER")
        add_column_if_missing(conn, "org_employees", "updated_at_ms INTEGER")

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_org_employees_source_key ON org_employees(source_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_employees_company_id ON org_employees(company_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_employees_department_id ON org_employees(department_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org_employees_employee_user_id ON org_employees(employee_user_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_org_employees_parent_sort ON org_employees(company_id, department_id, sort_order)"
    )


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


def _create_departments_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            department_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company_id INTEGER,
            parent_department_id INTEGER,
            source_key TEXT NOT NULL,
            source_department_id TEXT,
            level_no INTEGER NOT NULL,
            path_name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at_ms INTEGER NOT NULL,
            updated_at_ms INTEGER NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
            FOREIGN KEY (parent_department_id) REFERENCES departments(department_id) ON DELETE CASCADE
        )
        """
    )
    _create_departments_indexes(conn)


def _create_departments_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_company_id ON departments(company_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_parent_department_id ON departments(parent_department_id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_departments_source_key ON departments(source_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_source_department_id ON departments(source_department_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_path_name ON departments(path_name)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_departments_company_parent_sort ON departments(company_id, parent_department_id, sort_order)"
    )
