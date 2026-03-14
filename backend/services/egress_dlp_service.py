from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.services.egress_policy_store import EgressPolicyStore

_SENSITIVITY_LEVEL_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
_SENSITIVITY_LEVELS = ("low", "medium", "high")


def _max_level(left: str, right: str) -> str:
    l = str(left or "none").strip().lower()
    r = str(right or "none").strip().lower()
    return l if _SENSITIVITY_LEVEL_ORDER.get(l, 0) >= _SENSITIVITY_LEVEL_ORDER.get(r, 0) else r


@dataclass(frozen=True)
class EgressDlpResult:
    payload: Any
    payload_level: str
    hit_rules: list[dict[str, Any]]
    masked: bool


class EgressDlpService:
    def __init__(self, *, db_path: str | None = None) -> None:
        self._db_path = str(resolve_auth_db_path(db_path))
        self._store = EgressPolicyStore(db_path=self._db_path)

    @staticmethod
    def _scan_and_mask_text(
        text: str,
        *,
        rules: dict[str, list[str]],
        auto_desensitize: bool,
    ) -> tuple[str, str, list[dict[str, Any]], bool]:
        source = str(text or "")
        masked_text = source
        payload_level = "none"
        hits: list[dict[str, Any]] = []
        masked = False

        for level in _SENSITIVITY_LEVELS:
            for raw_rule in rules.get(level, []) or []:
                rule = str(raw_rule or "").strip()
                if not rule:
                    continue
                pattern = re.compile(re.escape(rule), flags=re.IGNORECASE)
                matches = pattern.findall(masked_text if auto_desensitize else source)
                count = int(len(matches))
                if count <= 0:
                    continue
                hits.append({"level": level, "rule": rule, "count": count})
                payload_level = _max_level(payload_level, level)
                if auto_desensitize:
                    masked_text = pattern.sub("***", masked_text)
                    masked = True
        return masked_text, payload_level, hits, masked

    @staticmethod
    def _merge_hits(hit_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[tuple[str, str], int] = {}
        for item in hit_rules:
            level = str(item.get("level") or "").strip().lower()
            rule = str(item.get("rule") or "").strip()
            count = int(item.get("count") or 0)
            if level not in _SENSITIVITY_LEVEL_ORDER or level == "none" or not rule or count <= 0:
                continue
            key = (level, rule)
            merged[key] = int(merged.get(key, 0)) + count
        out = [{"level": level, "rule": rule, "count": count} for (level, rule), count in merged.items()]
        out.sort(key=lambda x: (-_SENSITIVITY_LEVEL_ORDER.get(str(x.get("level") or "none"), 0), str(x.get("rule") or "")))
        return out

    def _process_payload_with_policy(self, payload: Any, *, policy) -> EgressDlpResult:
        if not bool(getattr(policy, "sensitive_classification_enabled", False)):
            return EgressDlpResult(payload=copy.deepcopy(payload), payload_level="none", hit_rules=[], masked=False)

        rules = {
            "low": list(getattr(policy, "sensitivity_rules", {}).get("low") or []),
            "medium": list(getattr(policy, "sensitivity_rules", {}).get("medium") or []),
            "high": list(getattr(policy, "sensitivity_rules", {}).get("high") or []),
        }
        auto_desensitize = bool(getattr(policy, "auto_desensitize_enabled", False))

        def _walk(value: Any) -> tuple[Any, str, list[dict[str, Any]], bool]:
            if isinstance(value, str):
                return self._scan_and_mask_text(
                    value,
                    rules=rules,
                    auto_desensitize=auto_desensitize,
                )
            if isinstance(value, list):
                next_items: list[Any] = []
                level = "none"
                hits: list[dict[str, Any]] = []
                masked = False
                for item in value:
                    next_item, item_level, item_hits, item_masked = _walk(item)
                    next_items.append(next_item)
                    level = _max_level(level, item_level)
                    hits.extend(item_hits)
                    masked = masked or item_masked
                return next_items, level, hits, masked
            if isinstance(value, dict):
                next_obj: dict[str, Any] = {}
                level = "none"
                hits: list[dict[str, Any]] = []
                masked = False
                for key, item in value.items():
                    next_item, item_level, item_hits, item_masked = _walk(item)
                    next_obj[str(key)] = next_item
                    level = _max_level(level, item_level)
                    hits.extend(item_hits)
                    masked = masked or item_masked
                return next_obj, level, hits, masked
            return copy.deepcopy(value), "none", [], False

        next_payload, payload_level, hit_rules, masked = _walk(payload)
        return EgressDlpResult(
            payload=next_payload,
            payload_level=payload_level,
            hit_rules=self._merge_hits(hit_rules),
            masked=masked,
        )

    def process_payload(self, payload: Any) -> EgressDlpResult:
        try:
            policy = self._store.get()
        except Exception:
            return EgressDlpResult(payload=copy.deepcopy(payload), payload_level="none", hit_rules=[], masked=False)
        return self._process_payload_with_policy(payload, policy=policy)

    def process_payload_with_policy(self, payload: Any, *, policy) -> EgressDlpResult:
        return self._process_payload_with_policy(payload, policy=policy)
