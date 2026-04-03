from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_electronic_signature_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "electronic_signature_challenges"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS electronic_signature_challenges (
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                issued_at_ms INTEGER NOT NULL,
                expires_at_ms INTEGER NOT NULL,
                consumed_at_ms INTEGER,
                consumed_by_action TEXT
            )
            """
        )

    add_column_if_missing(conn, "electronic_signature_challenges", "user_id TEXT")
    add_column_if_missing(conn, "electronic_signature_challenges", "token_hash TEXT")
    add_column_if_missing(conn, "electronic_signature_challenges", "issued_at_ms INTEGER")
    add_column_if_missing(conn, "electronic_signature_challenges", "expires_at_ms INTEGER")
    add_column_if_missing(conn, "electronic_signature_challenges", "consumed_at_ms INTEGER")
    add_column_if_missing(conn, "electronic_signature_challenges", "consumed_by_action TEXT")

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_esign_challenges_token_hash ON electronic_signature_challenges(token_hash)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_esign_challenges_user_id ON electronic_signature_challenges(user_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_esign_challenges_expires_at_ms ON electronic_signature_challenges(expires_at_ms)"
    )

    if not table_exists(conn, "electronic_signatures"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS electronic_signatures (
                signature_id TEXT PRIMARY KEY,
                record_type TEXT NOT NULL,
                record_id TEXT NOT NULL,
                action TEXT NOT NULL,
                meaning TEXT NOT NULL,
                reason TEXT NOT NULL,
                signed_by TEXT NOT NULL,
                signed_by_username TEXT NOT NULL,
                signed_at_ms INTEGER NOT NULL,
                sign_token_id TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                signature_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'signed',
                record_payload_json TEXT NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "electronic_signatures", "record_type TEXT")
    add_column_if_missing(conn, "electronic_signatures", "record_id TEXT")
    add_column_if_missing(conn, "electronic_signatures", "action TEXT")
    add_column_if_missing(conn, "electronic_signatures", "meaning TEXT")
    add_column_if_missing(conn, "electronic_signatures", "reason TEXT")
    add_column_if_missing(conn, "electronic_signatures", "signed_by TEXT")
    add_column_if_missing(conn, "electronic_signatures", "signed_by_username TEXT")
    add_column_if_missing(conn, "electronic_signatures", "signed_at_ms INTEGER")
    add_column_if_missing(conn, "electronic_signatures", "sign_token_id TEXT")
    add_column_if_missing(conn, "electronic_signatures", "record_hash TEXT")
    add_column_if_missing(conn, "electronic_signatures", "signature_hash TEXT")
    add_column_if_missing(conn, "electronic_signatures", "status TEXT NOT NULL DEFAULT 'signed'")
    add_column_if_missing(conn, "electronic_signatures", "record_payload_json TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_electronic_signatures_record ON electronic_signatures(record_type, record_id, signed_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_electronic_signatures_signed_by ON electronic_signatures(signed_by, signed_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_electronic_signatures_token_id ON electronic_signatures(sign_token_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_electronic_signatures_signature_hash ON electronic_signatures(signature_hash)"
    )
