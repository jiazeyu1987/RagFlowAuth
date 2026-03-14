from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

_ALLOWED_MODES = {"intranet", "extranet"}
_SENSITIVITY_LEVELS = ("low", "medium", "high")
_DEFAULT_DOMESTIC_MODEL_ALLOWLIST = ["qwen-plus", "glm-4-plus"]
_DEFAULT_SENSITIVITY_RULES = {
    "low": ["public"],
    "medium": ["internal"],
    "high": ["secret", "confidential"],
}


@dataclass(frozen=True)
class EgressPolicySettings:
    mode: str
    minimal_egress_enabled: bool
    sensitive_classification_enabled: bool
    auto_desensitize_enabled: bool
    high_sensitive_block_enabled: bool
    domestic_model_whitelist_enabled: bool
    domestic_model_allowlist: list[str]
    allowed_target_hosts: list[str]
    sensitivity_rules: dict[str, list[str]]
    updated_by_user_id: str
    updated_at_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "minimal_egress_enabled": self.minimal_egress_enabled,
            "sensitive_classification_enabled": self.sensitive_classification_enabled,
            "auto_desensitize_enabled": self.auto_desensitize_enabled,
            "high_sensitive_block_enabled": self.high_sensitive_block_enabled,
            "domestic_model_whitelist_enabled": self.domestic_model_whitelist_enabled,
            "domestic_model_allowlist": list(self.domestic_model_allowlist),
            "allowed_target_hosts": list(self.allowed_target_hosts),
            "sensitivity_rules": {
                "low": list(self.sensitivity_rules.get("low") or []),
                "medium": list(self.sensitivity_rules.get("medium") or []),
                "high": list(self.sensitivity_rules.get("high") or []),
            },
            "updated_by_user_id": self.updated_by_user_id,
            "updated_at_ms": self.updated_at_ms,
        }


def _normalize_bool(value: Any, *, field_name: str) -> bool:
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


def _normalize_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    if mode not in _ALLOWED_MODES:
        raise ValueError("invalid_mode")
    return mode


def _normalize_string_list(
    value: Any,
    *,
    field_name: str,
    lowercase: bool = True,
    max_items: int = 128,
    max_len: int = 255,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"invalid_{field_name}")
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        normalized = text.lower() if lowercase else text
        if len(normalized) > max_len:
            raise ValueError(f"invalid_{field_name}")
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    if len(out) > max_items:
        raise ValueError(f"invalid_{field_name}")
    return out


def _normalize_sensitivity_rules(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise ValueError("invalid_sensitivity_rules")
    unknown_levels = set(value.keys()) - set(_SENSITIVITY_LEVELS)
    if unknown_levels:
        raise ValueError("invalid_sensitivity_rules")
    normalized: dict[str, list[str]] = {}
    for level in _SENSITIVITY_LEVELS:
        normalized[level] = _normalize_string_list(
            value.get(level, []),
            field_name=f"sensitivity_rules_{level}",
            lowercase=False,
            max_items=256,
            max_len=128,
        )
    return normalized


def _safe_json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


class EgressPolicyStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _parse_row(row) -> EgressPolicySettings:
        whitelist_enabled = bool(row["domestic_model_whitelist_enabled"])
        allowlist = _safe_json_loads(row["domestic_model_allowlist_json"], _DEFAULT_DOMESTIC_MODEL_ALLOWLIST)
        if not isinstance(allowlist, list):
            allowlist = []
        allowlist = _normalize_string_list(
            allowlist,
            field_name="domestic_model_allowlist",
            lowercase=True,
            max_items=128,
            max_len=128,
        )
        if whitelist_enabled and not allowlist:
            allowlist = list(_DEFAULT_DOMESTIC_MODEL_ALLOWLIST)

        hosts = _safe_json_loads(row["allowed_target_hosts_json"], [])
        if not isinstance(hosts, list):
            hosts = []
        hosts = _normalize_string_list(hosts, field_name="allowed_target_hosts", lowercase=True, max_items=256)

        rules_raw = _safe_json_loads(row["sensitivity_rules_json"], _DEFAULT_SENSITIVITY_RULES)
        try:
            rules = _normalize_sensitivity_rules(rules_raw)
        except ValueError:
            rules = {k: list(v) for k, v in _DEFAULT_SENSITIVITY_RULES.items()}

        mode = str(row["mode"] or "intranet").strip().lower()
        if mode not in _ALLOWED_MODES:
            mode = "intranet"

        return EgressPolicySettings(
            mode=mode,
            minimal_egress_enabled=bool(row["minimal_egress_enabled"]),
            sensitive_classification_enabled=bool(row["sensitive_classification_enabled"]),
            auto_desensitize_enabled=bool(row["auto_desensitize_enabled"]),
            high_sensitive_block_enabled=bool(row["high_sensitive_block_enabled"]),
            domestic_model_whitelist_enabled=whitelist_enabled,
            domestic_model_allowlist=allowlist,
            allowed_target_hosts=hosts,
            sensitivity_rules=rules,
            updated_by_user_id=str(row["updated_by_user_id"] or ""),
            updated_at_ms=int(row["updated_at_ms"] or 0),
        )

    def get(self) -> EgressPolicySettings:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM egress_policy_settings WHERE id = 1").fetchone()
            if not row:
                raise RuntimeError("egress_policy_settings_not_initialized")
            return self._parse_row(row)
        finally:
            conn.close()

    def update(self, updates: dict[str, Any], *, actor_user_id: str | None = None) -> EgressPolicySettings:
        if not isinstance(updates, dict):
            raise ValueError("invalid_updates")

        current = self.get()
        fields: dict[str, Any] = {}

        if "mode" in updates:
            fields["mode"] = _normalize_mode(updates.get("mode"))

        if "minimal_egress_enabled" in updates:
            fields["minimal_egress_enabled"] = int(
                _normalize_bool(updates.get("minimal_egress_enabled"), field_name="minimal_egress_enabled")
            )
        if "sensitive_classification_enabled" in updates:
            fields["sensitive_classification_enabled"] = int(
                _normalize_bool(
                    updates.get("sensitive_classification_enabled"),
                    field_name="sensitive_classification_enabled",
                )
            )
        if "auto_desensitize_enabled" in updates:
            fields["auto_desensitize_enabled"] = int(
                _normalize_bool(updates.get("auto_desensitize_enabled"), field_name="auto_desensitize_enabled")
            )
        if "high_sensitive_block_enabled" in updates:
            fields["high_sensitive_block_enabled"] = int(
                _normalize_bool(
                    updates.get("high_sensitive_block_enabled"),
                    field_name="high_sensitive_block_enabled",
                )
            )
        if "domestic_model_whitelist_enabled" in updates:
            fields["domestic_model_whitelist_enabled"] = int(
                _normalize_bool(
                    updates.get("domestic_model_whitelist_enabled"),
                    field_name="domestic_model_whitelist_enabled",
                )
            )

        if "domestic_model_allowlist" in updates:
            allowlist = _normalize_string_list(
                updates.get("domestic_model_allowlist"),
                field_name="domestic_model_allowlist",
                lowercase=True,
                max_items=128,
                max_len=128,
            )
            fields["domestic_model_allowlist_json"] = json.dumps(
                allowlist,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        if "allowed_target_hosts" in updates:
            hosts = _normalize_string_list(
                updates.get("allowed_target_hosts"),
                field_name="allowed_target_hosts",
                lowercase=True,
                max_items=256,
                max_len=255,
            )
            fields["allowed_target_hosts_json"] = json.dumps(
                hosts,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        if "sensitivity_rules" in updates:
            rules = _normalize_sensitivity_rules(updates.get("sensitivity_rules"))
            fields["sensitivity_rules_json"] = json.dumps(
                rules,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        if not fields:
            raise ValueError("empty_updates")

        next_whitelist_enabled = bool(
            fields.get("domestic_model_whitelist_enabled", int(current.domestic_model_whitelist_enabled))
        )
        next_allowlist = current.domestic_model_allowlist
        if "domestic_model_allowlist_json" in fields:
            next_allowlist = _safe_json_loads(fields["domestic_model_allowlist_json"], [])
            if not isinstance(next_allowlist, list):
                next_allowlist = []
        if next_whitelist_enabled and not next_allowlist:
            raise ValueError("empty_domestic_model_allowlist")

        now_ms = int(time.time() * 1000)
        fields["updated_by_user_id"] = str(actor_user_id or "").strip()
        fields["updated_at_ms"] = now_ms

        conn = self._conn()
        try:
            sets = ", ".join(f"{column} = ?" for column in fields.keys())
            values = list(fields.values())
            values.append(1)
            cur = conn.execute(f"UPDATE egress_policy_settings SET {sets} WHERE id = ?", values)
            conn.commit()
            if (cur.rowcount or 0) <= 0:
                raise RuntimeError("egress_policy_settings_not_initialized")
        finally:
            conn.close()
        return self.get()
