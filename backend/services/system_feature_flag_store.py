from __future__ import annotations

import time
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

FLAG_PAPER_PLAG_ENABLED = "paper_plag_enabled"
FLAG_EGRESS_POLICY_ENABLED = "egress_policy_enabled"
FLAG_RESEARCH_UI_LAYOUT_ENABLED = "research_ui_layout_enabled"

ROLLBACK_FLAG_KEYS = (
    FLAG_PAPER_PLAG_ENABLED,
    FLAG_EGRESS_POLICY_ENABLED,
    FLAG_RESEARCH_UI_LAYOUT_ENABLED,
)


def _parse_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid_{field_name}")


class SystemFeatureFlagStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _base_payload() -> dict[str, bool]:
        return {
            FLAG_PAPER_PLAG_ENABLED: True,
            FLAG_EGRESS_POLICY_ENABLED: True,
            FLAG_RESEARCH_UI_LAYOUT_ENABLED: True,
        }

    def list_flags(self) -> dict[str, bool]:
        payload = self._base_payload()
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT flag_key, enabled
                FROM system_feature_flags
                WHERE flag_key IN (?, ?, ?)
                """,
                (
                    FLAG_PAPER_PLAG_ENABLED,
                    FLAG_EGRESS_POLICY_ENABLED,
                    FLAG_RESEARCH_UI_LAYOUT_ENABLED,
                ),
            ).fetchall()
        finally:
            conn.close()

        for row in rows or []:
            key = str(row["flag_key"] or "").strip()
            if key in payload:
                payload[key] = bool(row["enabled"])
        return payload

    def is_enabled(self, flag_key: str, *, default: bool = True) -> bool:
        normalized = str(flag_key or "").strip()
        if not normalized:
            return bool(default)
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT enabled FROM system_feature_flags WHERE flag_key = ?",
                (normalized,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return bool(default)
        return bool(row["enabled"])

    def update_flags(self, updates: dict[str, Any], *, actor_user_id: str = "") -> dict[str, bool]:
        if not isinstance(updates, dict):
            raise ValueError("invalid_updates")
        if not updates:
            raise ValueError("empty_updates")

        normalized: dict[str, int] = {}
        for key, value in updates.items():
            normalized_key = str(key or "").strip()
            if normalized_key not in ROLLBACK_FLAG_KEYS:
                raise ValueError(f"unsupported_flag_key:{normalized_key}")
            normalized[normalized_key] = int(_parse_bool(value, field_name=normalized_key))

        now_ms = int(time.time() * 1000)
        actor = str(actor_user_id or "").strip()
        conn = self._conn()
        try:
            for key, enabled in normalized.items():
                conn.execute(
                    """
                    INSERT INTO system_feature_flags (
                        flag_key,
                        enabled,
                        description,
                        updated_by_user_id,
                        updated_at_ms
                    )
                    VALUES (?, ?, '', ?, ?)
                    ON CONFLICT(flag_key) DO UPDATE SET
                        enabled = excluded.enabled,
                        updated_by_user_id = excluded.updated_by_user_id,
                        updated_at_ms = excluded.updated_at_ms
                    """,
                    (key, enabled, actor, now_ms),
                )
            conn.commit()
        finally:
            conn.close()
        return self.list_flags()

    def rollback_disable_all(self, *, actor_user_id: str = "") -> dict[str, bool]:
        now_ms = int(time.time() * 1000)
        actor = str(actor_user_id or "").strip()
        conn = self._conn()
        try:
            for key in ROLLBACK_FLAG_KEYS:
                conn.execute(
                    """
                    INSERT INTO system_feature_flags (
                        flag_key,
                        enabled,
                        description,
                        updated_by_user_id,
                        updated_at_ms
                    )
                    VALUES (?, 0, '', ?, ?)
                    ON CONFLICT(flag_key) DO UPDATE SET
                        enabled = 0,
                        updated_by_user_id = excluded.updated_by_user_id,
                        updated_at_ms = excluded.updated_at_ms
                    """,
                    (key, actor, now_ms),
                )
            conn.commit()
        finally:
            conn.close()
        return self.list_flags()
