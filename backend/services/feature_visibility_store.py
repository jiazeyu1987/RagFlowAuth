from __future__ import annotations

import time
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

FLAG_TOOL_NHSA_VISIBLE = "tool_nhsa_visible"
FLAG_TOOL_SH_TAX_VISIBLE = "tool_sh_tax_visible"
FLAG_TOOL_DRUG_ADMIN_VISIBLE = "tool_drug_admin_visible"
FLAG_TOOL_NMPA_VISIBLE = "tool_nmpa_visible"
FLAG_TOOL_NAS_VISIBLE = "tool_nas_visible"
FLAG_PAGE_DATA_SECURITY_TEST_VISIBLE = "page_data_security_test_visible"
FLAG_PAGE_LOGS_VISIBLE = "page_logs_visible"
FLAG_API_AUDIT_EVENTS_VISIBLE = "api_audit_events_visible"
FLAG_API_DIAGNOSTICS_VISIBLE = "api_diagnostics_visible"
FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE = "api_admin_feature_flags_visible"

VISIBILITY_FLAG_KEYS = (
    FLAG_TOOL_NHSA_VISIBLE,
    FLAG_TOOL_SH_TAX_VISIBLE,
    FLAG_TOOL_DRUG_ADMIN_VISIBLE,
    FLAG_TOOL_NMPA_VISIBLE,
    FLAG_TOOL_NAS_VISIBLE,
    FLAG_PAGE_DATA_SECURITY_TEST_VISIBLE,
    FLAG_PAGE_LOGS_VISIBLE,
    FLAG_API_AUDIT_EVENTS_VISIBLE,
    FLAG_API_DIAGNOSTICS_VISIBLE,
    FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE,
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


class FeatureVisibilityStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _default_payload() -> dict[str, bool]:
        return {
            FLAG_TOOL_NHSA_VISIBLE: True,
            FLAG_TOOL_SH_TAX_VISIBLE: True,
            FLAG_TOOL_DRUG_ADMIN_VISIBLE: True,
            FLAG_TOOL_NMPA_VISIBLE: True,
            FLAG_TOOL_NAS_VISIBLE: True,
            FLAG_PAGE_DATA_SECURITY_TEST_VISIBLE: True,
            FLAG_PAGE_LOGS_VISIBLE: True,
            FLAG_API_AUDIT_EVENTS_VISIBLE: True,
            FLAG_API_DIAGNOSTICS_VISIBLE: True,
            FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE: True,
        }

    def list_flags(self) -> dict[str, bool]:
        payload = self._default_payload()
        conn = self._conn()
        try:
            placeholders = ",".join("?" for _ in VISIBILITY_FLAG_KEYS)
            rows = conn.execute(
                f"""
                SELECT flag_key, enabled
                FROM system_feature_flags
                WHERE flag_key IN ({placeholders})
                """,
                VISIBILITY_FLAG_KEYS,
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
            if normalized_key not in VISIBILITY_FLAG_KEYS:
                raise ValueError(f"unsupported_visibility_flag_key:{normalized_key}")
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
