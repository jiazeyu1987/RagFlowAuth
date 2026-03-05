from __future__ import annotations

import json
import time
from dataclasses import dataclass

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


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

    def update_allowed_extensions(self, extensions: list[str]) -> UploadSettings:
        normalized = self._normalize_extensions(extensions)
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
        return self.get()

    def add_allowed_extension_if_missing(self, extension: str) -> UploadSettings:
        normalized = self._normalize_extensions([extension])
        ext = normalized[0]
        current = self.get()
        if ext in current.allowed_extensions:
            return current
        next_values = sorted(set(current.allowed_extensions) | {ext})
        return self.update_allowed_extensions(next_values)
