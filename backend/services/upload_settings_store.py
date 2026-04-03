from __future__ import annotations

import json
import time
from dataclasses import dataclass

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite
from backend.services.config_change_log_store import ConfigChangeLogStore


@dataclass(frozen=True)
class UploadSettings:
    allowed_extensions: list[str]
    updated_at_ms: int


class UploadSettingsStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _normalize_extensions(raw) -> list[str]:
        if not isinstance(raw, list):
            raise ValueError("invalid_extensions")
        out: list[str] = []
        seen = set()
        for item in raw:
            value = str(item or "").strip().lower()
            if not value:
                continue
            if not value.startswith("."):
                value = f".{value}"
            if len(value) < 2 or any(ch.isspace() for ch in value):
                raise ValueError("invalid_extensions")
            if value not in seen:
                seen.add(value)
                out.append(value)
        if not out:
            raise ValueError("empty_extensions")
        return sorted(out)

    def get(self) -> UploadSettings:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT value_json, updated_at_ms FROM upload_settings WHERE key = ?",
                ("allowed_extensions",),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            raise ValueError("settings_not_found")
        try:
            allowed = self._normalize_extensions(json.loads(row["value_json"] or "[]"))
        except Exception as e:
            raise ValueError(f"invalid_settings:{e}") from e
        return UploadSettings(
            allowed_extensions=allowed,
            updated_at_ms=int(row["updated_at_ms"] or 0),
        )

    def update_allowed_extensions(
        self,
        extensions: list[str],
        *,
        changed_by: str | None = None,
        change_reason: str | None = None,
        approved_by: str | None = None,
    ) -> UploadSettings:
        normalized = self._normalize_extensions(extensions)
        before = self.get()
        if normalized == before.allowed_extensions:
            return before

        if changed_by is not None or change_reason is not None or approved_by is not None:
            if not str(changed_by or "").strip():
                raise ValueError("changed_by_required")
            if not str(change_reason or "").strip():
                raise ValueError("change_reason_required")

        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE upload_settings
                SET value_json = ?, updated_at_ms = ?
                WHERE key = ?
                """,
                (json.dumps(normalized, ensure_ascii=False), now_ms, "allowed_extensions"),
            )
            conn.commit()
        finally:
            conn.close()
        updated = self.get()
        if changed_by is not None or change_reason is not None or approved_by is not None:
            ConfigChangeLogStore(db_path=self.db_path).log_change(
                config_domain="upload_allowed_extensions",
                before={"allowed_extensions": before.allowed_extensions},
                after={"allowed_extensions": updated.allowed_extensions},
                changed_by=str(changed_by).strip(),
                change_reason=str(change_reason).strip(),
                approved_by=(str(approved_by).strip() or None) if approved_by is not None else None,
            )
        return updated
