from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_unified_task_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "unified_tasks"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS unified_tasks (
                task_id TEXT PRIMARY KEY,
                task_kind TEXT NOT NULL,
                owner_user_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 100,
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                source_ref TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                result_json TEXT NOT NULL DEFAULT '{}',
                error_json TEXT NOT NULL DEFAULT '{}',
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                started_at_ms INTEGER,
                finished_at_ms INTEGER,
                canceled_at_ms INTEGER
            )
            """
        )
    else:
        add_column_if_missing(conn, "unified_tasks", "task_kind TEXT NOT NULL DEFAULT 'nas_import'")
        add_column_if_missing(conn, "unified_tasks", "owner_user_id TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "unified_tasks", "status TEXT NOT NULL DEFAULT 'pending'")
        add_column_if_missing(conn, "unified_tasks", "priority INTEGER NOT NULL DEFAULT 100")
        add_column_if_missing(conn, "unified_tasks", "retry_count INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "unified_tasks", "max_retries INTEGER NOT NULL DEFAULT 3")
        add_column_if_missing(conn, "unified_tasks", "source_ref TEXT")
        add_column_if_missing(conn, "unified_tasks", "payload_json TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "unified_tasks", "result_json TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "unified_tasks", "error_json TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "unified_tasks", "created_at_ms INTEGER")
        add_column_if_missing(conn, "unified_tasks", "updated_at_ms INTEGER")
        add_column_if_missing(conn, "unified_tasks", "started_at_ms INTEGER")
        add_column_if_missing(conn, "unified_tasks", "finished_at_ms INTEGER")
        add_column_if_missing(conn, "unified_tasks", "canceled_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_tasks_kind_status_priority ON unified_tasks(task_kind, status, priority)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_tasks_owner_status ON unified_tasks(owner_user_id, status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_tasks_updated_at ON unified_tasks(updated_at_ms DESC)"
    )

    if not table_exists(conn, "unified_task_jobs"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS unified_task_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                attempt_no INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'queued',
                queue_name TEXT NOT NULL DEFAULT 'default',
                worker_id TEXT,
                message TEXT,
                detail_json TEXT NOT NULL DEFAULT '{}',
                queued_at_ms INTEGER NOT NULL,
                started_at_ms INTEGER,
                finished_at_ms INTEGER,
                FOREIGN KEY (task_id) REFERENCES unified_tasks(task_id) ON DELETE CASCADE,
                UNIQUE(task_id, attempt_no)
            )
            """
        )
    else:
        add_column_if_missing(conn, "unified_task_jobs", "task_id TEXT")
        add_column_if_missing(conn, "unified_task_jobs", "attempt_no INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "unified_task_jobs", "status TEXT NOT NULL DEFAULT 'queued'")
        add_column_if_missing(conn, "unified_task_jobs", "queue_name TEXT NOT NULL DEFAULT 'default'")
        add_column_if_missing(conn, "unified_task_jobs", "worker_id TEXT")
        add_column_if_missing(conn, "unified_task_jobs", "message TEXT")
        add_column_if_missing(conn, "unified_task_jobs", "detail_json TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "unified_task_jobs", "queued_at_ms INTEGER")
        add_column_if_missing(conn, "unified_task_jobs", "started_at_ms INTEGER")
        add_column_if_missing(conn, "unified_task_jobs", "finished_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_task_jobs_task_attempt ON unified_task_jobs(task_id, attempt_no DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_task_jobs_status_queue ON unified_task_jobs(status, queue_name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_task_jobs_queued_at ON unified_task_jobs(queued_at_ms DESC)"
    )

    if not table_exists(conn, "unified_task_events"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS unified_task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                job_id INTEGER,
                event_type TEXT NOT NULL,
                event_status TEXT,
                message TEXT,
                detail_json TEXT NOT NULL DEFAULT '{}',
                created_at_ms INTEGER NOT NULL,
                FOREIGN KEY (task_id) REFERENCES unified_tasks(task_id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES unified_task_jobs(id) ON DELETE SET NULL
            )
            """
        )
    else:
        add_column_if_missing(conn, "unified_task_events", "task_id TEXT")
        add_column_if_missing(conn, "unified_task_events", "job_id INTEGER")
        add_column_if_missing(conn, "unified_task_events", "event_type TEXT NOT NULL DEFAULT 'unknown'")
        add_column_if_missing(conn, "unified_task_events", "event_status TEXT")
        add_column_if_missing(conn, "unified_task_events", "message TEXT")
        add_column_if_missing(conn, "unified_task_events", "detail_json TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "unified_task_events", "created_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_task_events_task_created ON unified_task_events(task_id, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_task_events_type_created ON unified_task_events(event_type, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_unified_task_events_job_created ON unified_task_events(job_id, created_at_ms DESC)"
    )
