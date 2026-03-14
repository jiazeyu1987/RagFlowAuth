from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_paper_plag_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "paper_versions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                version_no INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL DEFAULT '',
                content_hash TEXT,
                content_text TEXT,
                author_user_id TEXT NOT NULL DEFAULT '',
                note TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                UNIQUE(paper_id, version_no)
            )
            """
        )
    else:
        add_column_if_missing(conn, "paper_versions", "paper_id TEXT")
        add_column_if_missing(conn, "paper_versions", "version_no INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "paper_versions", "title TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "paper_versions", "content_hash TEXT")
        add_column_if_missing(conn, "paper_versions", "content_text TEXT")
        add_column_if_missing(conn, "paper_versions", "author_user_id TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "paper_versions", "note TEXT")
        add_column_if_missing(conn, "paper_versions", "created_at_ms INTEGER")
        add_column_if_missing(conn, "paper_versions", "updated_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_versions_paper_created ON paper_versions(paper_id, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_versions_author_updated ON paper_versions(author_user_id, updated_at_ms DESC)"
    )

    if not table_exists(conn, "paper_plag_reports"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_plag_reports (
                report_id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                version_id INTEGER,
                task_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                score REAL NOT NULL DEFAULT 0,
                duplicate_rate REAL NOT NULL DEFAULT 0,
                summary TEXT,
                source_count INTEGER NOT NULL DEFAULT 0,
                report_file_path TEXT,
                created_by_user_id TEXT NOT NULL DEFAULT '',
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                finished_at_ms INTEGER,
                FOREIGN KEY (version_id) REFERENCES paper_versions(id) ON DELETE SET NULL
            )
            """
        )
    else:
        add_column_if_missing(conn, "paper_plag_reports", "paper_id TEXT")
        add_column_if_missing(conn, "paper_plag_reports", "version_id INTEGER")
        add_column_if_missing(conn, "paper_plag_reports", "task_id TEXT")
        add_column_if_missing(conn, "paper_plag_reports", "status TEXT NOT NULL DEFAULT 'pending'")
        add_column_if_missing(conn, "paper_plag_reports", "score REAL NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "paper_plag_reports", "duplicate_rate REAL NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "paper_plag_reports", "summary TEXT")
        add_column_if_missing(conn, "paper_plag_reports", "source_count INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "paper_plag_reports", "report_file_path TEXT")
        add_column_if_missing(conn, "paper_plag_reports", "created_by_user_id TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "paper_plag_reports", "created_at_ms INTEGER")
        add_column_if_missing(conn, "paper_plag_reports", "updated_at_ms INTEGER")
        add_column_if_missing(conn, "paper_plag_reports", "finished_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_plag_reports_paper_created ON paper_plag_reports(paper_id, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_plag_reports_status_created ON paper_plag_reports(status, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_plag_reports_task_id ON paper_plag_reports(task_id)"
    )

    if not table_exists(conn, "paper_plag_hits"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_plag_hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                source_doc_id TEXT,
                source_title TEXT,
                source_uri TEXT,
                similarity_score REAL NOT NULL DEFAULT 0,
                start_offset INTEGER NOT NULL DEFAULT 0,
                end_offset INTEGER NOT NULL DEFAULT 0,
                snippet_text TEXT,
                created_at_ms INTEGER NOT NULL,
                FOREIGN KEY (report_id) REFERENCES paper_plag_reports(report_id) ON DELETE CASCADE
            )
            """
        )
    else:
        add_column_if_missing(conn, "paper_plag_hits", "report_id TEXT")
        add_column_if_missing(conn, "paper_plag_hits", "source_doc_id TEXT")
        add_column_if_missing(conn, "paper_plag_hits", "source_title TEXT")
        add_column_if_missing(conn, "paper_plag_hits", "source_uri TEXT")
        add_column_if_missing(conn, "paper_plag_hits", "similarity_score REAL NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "paper_plag_hits", "start_offset INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "paper_plag_hits", "end_offset INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "paper_plag_hits", "snippet_text TEXT")
        add_column_if_missing(conn, "paper_plag_hits", "created_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_plag_hits_report_similarity ON paper_plag_hits(report_id, similarity_score DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_plag_hits_report_offset ON paper_plag_hits(report_id, start_offset, end_offset)"
    )


def ensure_egress_decision_audits_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "egress_decision_audits"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS egress_decision_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                actor_user_id TEXT NOT NULL DEFAULT '',
                policy_mode TEXT NOT NULL DEFAULT 'intranet',
                decision TEXT NOT NULL,
                hit_rules_json TEXT NOT NULL DEFAULT '[]',
                reason TEXT,
                target_host TEXT,
                target_model TEXT,
                payload_level TEXT,
                request_meta_json TEXT NOT NULL DEFAULT '{}',
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    else:
        add_column_if_missing(conn, "egress_decision_audits", "request_id TEXT")
        add_column_if_missing(conn, "egress_decision_audits", "actor_user_id TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "egress_decision_audits", "policy_mode TEXT NOT NULL DEFAULT 'intranet'")
        add_column_if_missing(conn, "egress_decision_audits", "decision TEXT NOT NULL DEFAULT 'allow'")
        add_column_if_missing(conn, "egress_decision_audits", "hit_rules_json TEXT NOT NULL DEFAULT '[]'")
        add_column_if_missing(conn, "egress_decision_audits", "reason TEXT")
        add_column_if_missing(conn, "egress_decision_audits", "target_host TEXT")
        add_column_if_missing(conn, "egress_decision_audits", "target_model TEXT")
        add_column_if_missing(conn, "egress_decision_audits", "payload_level TEXT")
        add_column_if_missing(conn, "egress_decision_audits", "request_meta_json TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "egress_decision_audits", "created_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_egress_decision_audits_created ON egress_decision_audits(created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_egress_decision_audits_actor_created ON egress_decision_audits(actor_user_id, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_egress_decision_audits_decision_created ON egress_decision_audits(decision, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_egress_decision_audits_target_host ON egress_decision_audits(target_host)"
    )


def ensure_egress_policy_settings_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "egress_policy_settings"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS egress_policy_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mode TEXT NOT NULL DEFAULT 'intranet',
                minimal_egress_enabled INTEGER NOT NULL DEFAULT 1,
                sensitive_classification_enabled INTEGER NOT NULL DEFAULT 1,
                auto_desensitize_enabled INTEGER NOT NULL DEFAULT 1,
                high_sensitive_block_enabled INTEGER NOT NULL DEFAULT 1,
                domestic_model_whitelist_enabled INTEGER NOT NULL DEFAULT 1,
                domestic_model_allowlist_json TEXT NOT NULL DEFAULT '[]',
                allowed_target_hosts_json TEXT NOT NULL DEFAULT '[]',
                sensitivity_rules_json TEXT NOT NULL DEFAULT '{}',
                updated_by_user_id TEXT NOT NULL DEFAULT '',
                updated_at_ms INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    else:
        add_column_if_missing(conn, "egress_policy_settings", "mode TEXT NOT NULL DEFAULT 'intranet'")
        add_column_if_missing(conn, "egress_policy_settings", "minimal_egress_enabled INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(
            conn, "egress_policy_settings", "sensitive_classification_enabled INTEGER NOT NULL DEFAULT 1"
        )
        add_column_if_missing(conn, "egress_policy_settings", "auto_desensitize_enabled INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "egress_policy_settings", "high_sensitive_block_enabled INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(
            conn, "egress_policy_settings", "domestic_model_whitelist_enabled INTEGER NOT NULL DEFAULT 1"
        )
        add_column_if_missing(conn, "egress_policy_settings", "domestic_model_allowlist_json TEXT NOT NULL DEFAULT '[]'")
        add_column_if_missing(conn, "egress_policy_settings", "allowed_target_hosts_json TEXT NOT NULL DEFAULT '[]'")
        add_column_if_missing(conn, "egress_policy_settings", "sensitivity_rules_json TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "egress_policy_settings", "updated_by_user_id TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "egress_policy_settings", "updated_at_ms INTEGER NOT NULL DEFAULT 0")

    conn.execute(
        """
        INSERT OR IGNORE INTO egress_policy_settings (
            id,
            mode,
            minimal_egress_enabled,
            sensitive_classification_enabled,
            auto_desensitize_enabled,
            high_sensitive_block_enabled,
            domestic_model_whitelist_enabled,
            domestic_model_allowlist_json,
            allowed_target_hosts_json,
            sensitivity_rules_json,
            updated_by_user_id,
            updated_at_ms
        )
        VALUES (
            1,
            'intranet',
            1,
            1,
            1,
            1,
            1,
            '["qwen-plus","glm-4-plus"]',
            '[]',
            '{"low":["public"],"medium":["internal"],"high":["secret","confidential"]}',
            '',
            CAST(strftime('%s', 'now') AS INTEGER) * 1000
        )
        """
    )


def ensure_system_feature_flags_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "system_feature_flags"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_feature_flags (
                flag_key TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                description TEXT NOT NULL DEFAULT '',
                updated_by_user_id TEXT NOT NULL DEFAULT '',
                updated_at_ms INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    else:
        add_column_if_missing(conn, "system_feature_flags", "flag_key TEXT")
        add_column_if_missing(conn, "system_feature_flags", "enabled INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "system_feature_flags", "description TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "system_feature_flags", "updated_by_user_id TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "system_feature_flags", "updated_at_ms INTEGER NOT NULL DEFAULT 0")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_system_feature_flags_enabled ON system_feature_flags(enabled)"
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO system_feature_flags (
            flag_key,
            enabled,
            description,
            updated_by_user_id,
            updated_at_ms
        )
        VALUES (
            'paper_plag_enabled',
            1,
            'Enable paper plagiarism module routes and processing.',
            '',
            CAST(strftime('%s', 'now') AS INTEGER) * 1000
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO system_feature_flags (
            flag_key,
            enabled,
            description,
            updated_by_user_id,
            updated_at_ms
        )
        VALUES (
            'egress_policy_enabled',
            1,
            'Enable egress mode and payload policy enforcement.',
            '',
            CAST(strftime('%s', 'now') AS INTEGER) * 1000
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO system_feature_flags (
            flag_key,
            enabled,
            description,
            updated_by_user_id,
            updated_at_ms
        )
        VALUES (
            'research_ui_layout_enabled',
            1,
            'Enable new research workbench three-pane layout.',
            '',
            CAST(strftime('%s', 'now') AS INTEGER) * 1000
        )
        """
    )
