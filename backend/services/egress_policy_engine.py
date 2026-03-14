from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.services.egress_dlp_service import EgressDlpService
from backend.services.egress_policy_store import EgressPolicyStore
from backend.services.system_feature_flag_store import FLAG_EGRESS_POLICY_ENABLED, SystemFeatureFlagStore

_MINIMAL_EGRESS_DROP_KEYS = {
    "attachment",
    "attachments",
    "file",
    "files",
    "file_data",
    "file_content",
    "file_contents",
    "binary",
    "binary_data",
    "blob",
    "base64",
    "base64_data",
    "raw",
    "raw_text",
    "raw_content",
    "raw_document",
    "raw_documents",
    "full_text",
    "full_content",
    "full_document",
    "full_documents",
    "source_document",
    "source_documents",
    "context_document",
    "context_documents",
    "chunk_data",
    "chunk_list",
    "chunks",
}
_MINIMAL_EGRESS_KEEP_FULL_TEXT_KEYS = {"question", "prompt", "content"}
_MINIMAL_EGRESS_MAX_STRING_LENGTH = 4096
_MINIMAL_EGRESS_MAX_LIST_ITEMS = 128
_MINIMAL_EGRESS_MAX_DICT_ITEMS = 128


@dataclass(frozen=True)
class EgressPolicyDecision:
    allowed: bool
    blocked_reason: str | None
    policy_mode: str
    sanitized_payload: dict[str, Any]
    payload_level: str
    hit_rules: list[dict[str, Any]]
    target_model: str | None
    masked: bool


class EgressPolicyEngine:
    def __init__(self, *, db_path: str | None = None) -> None:
        self._db_path = str(resolve_auth_db_path(db_path))
        self._store = EgressPolicyStore(db_path=self._db_path)
        self._dlp_service = EgressDlpService(db_path=self._db_path)
        self._feature_flag_store = SystemFeatureFlagStore(db_path=self._db_path)

    @staticmethod
    def _extract_target_model(payload: dict[str, Any]) -> str | None:
        model_keys = {"model", "model_name", "target_model", "llm", "llm_name"}
        queue: list[Any] = [payload]
        scanned = 0
        while queue and scanned < 1024:
            scanned += 1
            node = queue.pop(0)
            if isinstance(node, dict):
                for key, value in node.items():
                    text_key = str(key or "").strip().lower()
                    if text_key in model_keys and isinstance(value, str):
                        model = str(value or "").strip().lower()
                        if model:
                            return model
                    queue.append(value)
            elif isinstance(node, list):
                queue.extend(node)
        return None

    @classmethod
    def _apply_minimal_egress(cls, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        def _walk(value: Any, *, parent_key: str = "") -> tuple[Any, bool]:
            if isinstance(value, dict):
                next_obj: dict[str, Any] = {}
                changed = False
                kept = 0
                for raw_key, item in value.items():
                    key = str(raw_key or "")
                    normalized_key = key.strip().lower()
                    if normalized_key in _MINIMAL_EGRESS_DROP_KEYS:
                        changed = True
                        continue
                    if kept >= _MINIMAL_EGRESS_MAX_DICT_ITEMS:
                        changed = True
                        break
                    next_item, item_changed = _walk(item, parent_key=normalized_key)
                    next_obj[key] = next_item
                    kept += 1
                    changed = changed or item_changed
                return next_obj, changed

            if isinstance(value, list):
                next_items: list[Any] = []
                changed = False
                for idx, item in enumerate(value):
                    if idx >= _MINIMAL_EGRESS_MAX_LIST_ITEMS:
                        changed = True
                        break
                    next_item, item_changed = _walk(item, parent_key=parent_key)
                    next_items.append(next_item)
                    changed = changed or item_changed
                return next_items, changed

            if isinstance(value, str):
                if parent_key in _MINIMAL_EGRESS_KEEP_FULL_TEXT_KEYS:
                    return value, False
                if len(value) <= _MINIMAL_EGRESS_MAX_STRING_LENGTH:
                    return value, False
                return f"{value[:_MINIMAL_EGRESS_MAX_STRING_LENGTH]}...[truncated]", True

            if isinstance(value, (bytes, bytearray, memoryview)):
                return f"[binary_omitted:{len(bytes(value))}_bytes]", True

            return copy.deepcopy(value), False

        minimized, changed = _walk(payload)
        if isinstance(minimized, dict):
            return minimized, changed
        return {}, True

    def evaluate_payload(self, payload: dict[str, Any] | None) -> EgressPolicyDecision:
        candidate = copy.deepcopy(payload or {})
        if not isinstance(candidate, dict):
            candidate = {}
        target_model = self._extract_target_model(candidate)

        try:
            feature_enabled = self._feature_flag_store.is_enabled(
                FLAG_EGRESS_POLICY_ENABLED,
                default=True,
            )
        except Exception:
            feature_enabled = True
        if not feature_enabled:
            return EgressPolicyDecision(
                allowed=True,
                blocked_reason=None,
                policy_mode="feature_disabled",
                sanitized_payload=candidate,
                payload_level="none",
                hit_rules=[],
                target_model=target_model,
                masked=False,
            )

        try:
            policy = self._store.get()
        except Exception:
            return EgressPolicyDecision(
                allowed=True,
                blocked_reason=None,
                policy_mode="unknown",
                sanitized_payload=candidate,
                payload_level="none",
                hit_rules=[],
                target_model=target_model,
                masked=False,
            )

        dlp_result = self._dlp_service.process_payload_with_policy(candidate, policy=policy)
        sanitized_payload = dlp_result.payload if isinstance(dlp_result.payload, dict) else candidate

        mode = str(getattr(policy, "mode", "intranet") or "intranet").strip().lower()
        payload_level = str(dlp_result.payload_level or "none").strip().lower()
        target_model = self._extract_target_model(sanitized_payload) or target_model
        if mode == "extranet" and bool(getattr(policy, "minimal_egress_enabled", False)):
            minimized_payload, _ = self._apply_minimal_egress(sanitized_payload)
            sanitized_payload = minimized_payload

        # In intranet mode, external egress is already blocked by mode gateway/rules.
        # Model whitelist + high-sensitive hard block are enforced for extranet flow.
        if mode == "extranet":
            if bool(getattr(policy, "high_sensitive_block_enabled", False)) and payload_level == "high":
                return EgressPolicyDecision(
                    allowed=False,
                    blocked_reason="egress_blocked_high_sensitive_payload",
                    policy_mode=mode,
                    sanitized_payload=sanitized_payload,
                    payload_level=payload_level,
                    hit_rules=dlp_result.hit_rules,
                    target_model=target_model,
                    masked=bool(dlp_result.masked),
                )

            if bool(getattr(policy, "domestic_model_whitelist_enabled", False)) and target_model:
                allowlist = {
                    str(item or "").strip().lower()
                    for item in (getattr(policy, "domestic_model_allowlist", []) or [])
                    if str(item or "").strip()
                }
                if target_model not in allowlist:
                    return EgressPolicyDecision(
                        allowed=False,
                        blocked_reason=f"egress_blocked_model_not_allowed:{target_model}",
                        policy_mode=mode,
                        sanitized_payload=sanitized_payload,
                        payload_level=payload_level,
                        hit_rules=dlp_result.hit_rules,
                        target_model=target_model,
                        masked=bool(dlp_result.masked),
                    )

        return EgressPolicyDecision(
            allowed=True,
            blocked_reason=None,
            policy_mode=mode,
            sanitized_payload=sanitized_payload,
            payload_level=payload_level,
            hit_rules=dlp_result.hit_rules,
            target_model=target_model,
            masked=bool(dlp_result.masked),
        )
