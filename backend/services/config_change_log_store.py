from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class ConfigChangeLogEntry:
    id: int
    config_domain: str
    before_json: str
    after_json: str
    changed_by: str
    change_reason: str
    approved_by: str | None
    created_at_ms: int


class ConfigChangeLogStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _json_text(payload: Any) -> str:
        return json.dumps(payload if payload is not None else {}, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _row_to_entry(row) -> ConfigChangeLogEntry:
        return ConfigChangeLogEntry(
            id=int(row["id"]),
            config_domain=str(row["config_domain"]),
            before_json=str(row["before_json"] or "{}"),
            after_json=str(row["after_json"] or "{}"),
            changed_by=str(row["changed_by"]),
            change_reason=str(row["change_reason"]),
            approved_by=(str(row["approved_by"]) if row["approved_by"] else None),
            created_at_ms=int(row["created_at_ms"] or 0),
        )

    def log_change(
        self,
        *,
        config_domain: str,
        before: Any,
        after: Any,
        changed_by: str,
        change_reason: str,
        approved_by: str | None = None,
    ) -> ConfigChangeLogEntry:
        domain = str(config_domain or "").strip()
        actor = str(changed_by or "").strip()
        reason = str(change_reason or "").strip()
        approver = str(approved_by or "").strip() or None
        if not domain:
            raise ValueError("config_domain_required")
        if not actor:
            raise ValueError("changed_by_required")
        if not reason:
            raise ValueError("change_reason_required")

        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            cursor = conn.execute(
                """
                INSERT INTO config_change_logs (
                    config_domain,
                    before_json,
                    after_json,
                    changed_by,
                    change_reason,
                    approved_by,
                    created_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    domain,
                    self._json_text(before),
                    self._json_text(after),
                    actor,
                    reason,
                    approver,
                    now_ms,
                ),
            )
            entry_id = int(cursor.lastrowid)
            conn.commit()
        finally:
            conn.close()
        return self.get(entry_id)

    def get(self, entry_id: int) -> ConfigChangeLogEntry:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM config_change_logs WHERE id = ?", (int(entry_id),)).fetchone()
            if not row:
                raise KeyError(f"config change log not found: {entry_id}")
            return self._row_to_entry(row)
        finally:
            conn.close()

    def list_logs(self, *, config_domain: str | None = None, limit: int = 100) -> list[ConfigChangeLogEntry]:
        limit = int(max(1, min(500, limit)))
        conn = self._conn()
        try:
            query = "SELECT * FROM config_change_logs WHERE 1=1"
            params: list[Any] = []
            if config_domain:
                query += " AND config_domain = ?"
                params.append(str(config_domain))
            query += " ORDER BY created_at_ms DESC, id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_entry(row) for row in rows]
        finally:
            conn.close()
