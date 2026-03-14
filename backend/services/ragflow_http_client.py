from __future__ import annotations

import ast
import json
import logging
import os
import time
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Any, Iterator

import requests

from backend.app.core.request_id import get_request_id
from .egress_decision_audit_store import EgressDecisionAuditStore
from .egress_mode_runtime import EgressModeRuntime
from .egress_policy_engine import EgressPolicyDecision, EgressPolicyEngine


@dataclass(frozen=True)
class RagflowHttpClientConfig:
    base_url: str
    api_key: str
    timeout_s: float = 10.0


class RagflowHttpClient:
    def __init__(self, config: RagflowHttpClientConfig, *, logger: logging.Logger | None = None):
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._egress_runtime: EgressModeRuntime | None = None
        self._egress_policy_engine: EgressPolicyEngine | None = None
        self._egress_audit_store: EgressDecisionAuditStore | None = None

    @property
    def config(self) -> RagflowHttpClientConfig:
        return self._config

    def set_config(self, config: RagflowHttpClientConfig) -> None:
        self._config = config

    def headers(self) -> dict[str, str]:
        return self._headers()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

    def _timeout(self, timeout_s: float | None) -> float:
        return float(timeout_s if timeout_s is not None else self._config.timeout_s)

    def _stream_timeout(self, timeout_s: float | None) -> tuple[float, float]:
        """
        Streaming timeout strategy:
        - connect timeout: short (fail fast on unreachable upstream)
        - read timeout: longer than normal request to tolerate slow first token / pauses
        """
        base = self._timeout(timeout_s)
        connect_timeout = max(1.0, min(base, 10.0))
        read_timeout = 180.0
        raw = str(os.getenv("RAGFLOWAUTH_SSE_READ_TIMEOUT_S", "") or "").strip()
        if raw:
            try:
                parsed = float(raw)
                if parsed > 0:
                    read_timeout = parsed
            except Exception:
                pass
        return connect_timeout, read_timeout

    def _runtime_guard(self) -> EgressModeRuntime:
        if self._egress_runtime is None:
            self._egress_runtime = EgressModeRuntime()
        return self._egress_runtime

    def _policy_engine_guard(self) -> EgressPolicyEngine:
        if self._egress_policy_engine is None:
            self._egress_policy_engine = EgressPolicyEngine()
        return self._egress_policy_engine

    def _audit_store_guard(self) -> EgressDecisionAuditStore:
        if self._egress_audit_store is None:
            self._egress_audit_store = EgressDecisionAuditStore()
        return self._egress_audit_store

    @staticmethod
    def _extract_host(url: str) -> str:
        try:
            parsed = urlparse(str(url or ""))
            return str(parsed.hostname or "").strip().lower()
        except Exception:
            return ""

    def _audit_decision(
        self,
        *,
        decision: str,
        policy_mode: str,
        reason: str | None,
        target_host: str | None,
        target_model: str | None = None,
        payload_level: str | None = None,
        hit_rules: list[dict[str, Any]] | None = None,
        request_meta: dict[str, Any] | None = None,
    ) -> None:
        try:
            self._audit_store_guard().log_decision(
                request_id=get_request_id(),
                actor_user_id="",
                policy_mode=policy_mode,
                decision=decision,
                hit_rules=hit_rules or [],
                reason=reason,
                target_host=target_host,
                target_model=target_model,
                payload_level=payload_level,
                request_meta=request_meta or {},
            )
        except Exception:
            # Audit must not block primary request flow.
            return

    def _apply_outbound_policy(
        self,
        body: dict[str, Any] | None,
        *,
        operation: str,
    ) -> tuple[dict[str, Any], EgressPolicyDecision | None]:
        candidate = body or {}
        if not isinstance(candidate, dict):
            return (body if body is not None else {}), None
        try:
            decision = self._policy_engine_guard().evaluate_payload(candidate)
        except Exception as exc:
            self._logger.warning("RAGFlow %s egress policy processing failed; fallback to original payload: %s", operation, exc)
            return candidate, None
        if decision.masked:
            self._logger.info(
                "RAGFlow %s payload desensitized: level=%s hit_rule_count=%s",
                operation,
                decision.payload_level,
                len(decision.hit_rules),
            )
        if not decision.allowed:
            reason = str(decision.blocked_reason or "egress_blocked_by_policy")
            self._logger.warning("RAGFlow %s blocked by egress policy engine: %s", operation, reason)
            return candidate, decision
        if isinstance(decision.sanitized_payload, dict):
            return decision.sanitized_payload, decision
        return candidate, decision

    def _is_egress_blocked(self, *, url: str, operation: str) -> tuple[bool, str, str, str]:
        try:
            decision = self._runtime_guard().evaluate_target(
                url,
                source=f"ragflow_http_client:{operation}",
            )
        except Exception:
            # Keep compatibility if runtime policy layer is unavailable.
            return False, "", "unknown", self._extract_host(url)
        if decision.allowed:
            return False, "", decision.mode, decision.host
        reason = str(decision.reason or "egress_blocked_by_mode")
        self._logger.warning(
            "RAGFlow %s blocked by egress policy: mode=%s host=%s reason=%s",
            operation,
            decision.mode,
            decision.host,
            reason,
        )
        return True, reason, decision.mode, decision.host

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        blocked, reason, mode, host = self._is_egress_blocked(url=url, operation="GET")
        if blocked:
            self._audit_decision(
                decision="block",
                policy_mode=mode,
                reason=reason,
                target_host=host,
                request_meta={"operation": "GET", "path": path},
            )
            return None
        self._audit_decision(
            decision="allow",
            policy_mode=mode,
            reason=None,
            target_host=host,
            request_meta={"operation": "GET", "path": path},
        )
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=self._timeout(None))
        except Exception as exc:
            self._logger.error("RAGFlow GET %s failed: %s", url, exc)
            return None

        if resp.status_code != 200:
            self._logger.error("RAGFlow GET %s failed: HTTP %s", url, resp.status_code)
            return None

        try:
            data = resp.json()
        except Exception as exc:
            self._logger.error("RAGFlow GET %s invalid JSON: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None

    def post_json(
        self, path: str, *, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        blocked, reason, mode, host = self._is_egress_blocked(url=url, operation="POST")
        if blocked:
            self._audit_decision(
                decision="block",
                policy_mode=mode,
                reason=reason,
                target_host=host,
                request_meta={"operation": "POST", "path": path},
            )
            return None
        sanitized_body, policy_decision = self._apply_outbound_policy(body, operation="POST")
        if policy_decision is not None and not policy_decision.allowed:
            self._audit_decision(
                decision="block",
                policy_mode=str(policy_decision.policy_mode or mode),
                reason=policy_decision.blocked_reason,
                target_host=host,
                target_model=policy_decision.target_model,
                payload_level=policy_decision.payload_level,
                hit_rules=policy_decision.hit_rules,
                request_meta={"operation": "POST", "path": path},
            )
            return None
        self._audit_decision(
            decision="allow",
            policy_mode=str((policy_decision.policy_mode if policy_decision else mode) or mode),
            reason=None,
            target_host=host,
            target_model=(policy_decision.target_model if policy_decision else None),
            payload_level=(policy_decision.payload_level if policy_decision else None),
            hit_rules=(policy_decision.hit_rules if policy_decision else None),
            request_meta={"operation": "POST", "path": path},
        )
        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                params=params,
                json=sanitized_body,
                timeout=self._timeout(None),
            )
        except Exception as exc:
            self._logger.error("RAGFlow POST %s failed: %s", url, exc)
            return None

        if resp.status_code != 200:
            body_preview = ""
            try:
                body_preview = (resp.text or "")[:500]
            except Exception:
                body_preview = ""
            if body_preview:
                self._logger.error("RAGFlow POST %s failed: HTTP %s body=%s", url, resp.status_code, body_preview)
            else:
                self._logger.error("RAGFlow POST %s failed: HTTP %s", url, resp.status_code)
            return None

        try:
            data = resp.json()
        except Exception as exc:
            self._logger.error("RAGFlow POST %s invalid JSON: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None

    def post_json_with_fallback(
        self, path: str, *, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Prefer JSON payload; when JSON parsing fails or HTTP/request fails,
        return a structured error object containing raw response text when available.
        """
        url = f"{self._config.base_url.rstrip('/')}{path}"
        blocked, reason, mode, host = self._is_egress_blocked(url=url, operation="POST")
        if blocked:
            self._audit_decision(
                decision="block",
                policy_mode=mode,
                reason=reason,
                target_host=host,
                request_meta={"operation": "POST", "path": path},
            )
            return {"code": 403, "message": reason}
        sanitized_body, policy_decision = self._apply_outbound_policy(body, operation="POST")
        if policy_decision is not None and not policy_decision.allowed:
            self._audit_decision(
                decision="block",
                policy_mode=str(policy_decision.policy_mode or mode),
                reason=policy_decision.blocked_reason,
                target_host=host,
                target_model=policy_decision.target_model,
                payload_level=policy_decision.payload_level,
                hit_rules=policy_decision.hit_rules,
                request_meta={"operation": "POST", "path": path},
            )
            return {"code": 403, "message": str(policy_decision.blocked_reason or "egress_blocked_by_policy")}
        self._audit_decision(
            decision="allow",
            policy_mode=str((policy_decision.policy_mode if policy_decision else mode) or mode),
            reason=None,
            target_host=host,
            target_model=(policy_decision.target_model if policy_decision else None),
            payload_level=(policy_decision.payload_level if policy_decision else None),
            hit_rules=(policy_decision.hit_rules if policy_decision else None),
            request_meta={"operation": "POST", "path": path},
        )
        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                params=params,
                json=sanitized_body,
                timeout=self._timeout(None),
            )
        except Exception as exc:
            self._logger.error("RAGFlow POST %s failed: %s", url, exc)
            return {"code": -1, "message": f"request_failed: {exc}"}

        raw_text = ""
        try:
            raw_text = str(resp.text or "")
        except Exception:
            raw_text = ""

        if resp.status_code != 200:
            preview = raw_text[:500] if raw_text else ""
            if preview:
                self._logger.error("RAGFlow POST %s failed: HTTP %s body=%s", url, resp.status_code, preview)
            else:
                self._logger.error("RAGFlow POST %s failed: HTTP %s", url, resp.status_code)
            return {
                "code": resp.status_code,
                "message": f"http_{resp.status_code}",
                "raw_text": preview,
            }

        try:
            data = resp.json()
            if isinstance(data, dict):
                return data
            return {"code": -1, "message": "invalid_json_root", "raw_text": raw_text[:500]}
        except Exception as exc:
            self._logger.error("RAGFlow POST %s invalid JSON: %s", url, exc)
            return {
                "code": -1,
                "message": f"invalid_json: {exc}",
                "raw_text": raw_text[:500],
            }

    def put_json(
        self, path: str, *, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        blocked, reason, mode, host = self._is_egress_blocked(url=url, operation="PUT")
        if blocked:
            self._audit_decision(
                decision="block",
                policy_mode=mode,
                reason=reason,
                target_host=host,
                request_meta={"operation": "PUT", "path": path},
            )
            return None
        sanitized_body, policy_decision = self._apply_outbound_policy(body, operation="PUT")
        if policy_decision is not None and not policy_decision.allowed:
            self._audit_decision(
                decision="block",
                policy_mode=str(policy_decision.policy_mode or mode),
                reason=policy_decision.blocked_reason,
                target_host=host,
                target_model=policy_decision.target_model,
                payload_level=policy_decision.payload_level,
                hit_rules=policy_decision.hit_rules,
                request_meta={"operation": "PUT", "path": path},
            )
            return None
        self._audit_decision(
            decision="allow",
            policy_mode=str((policy_decision.policy_mode if policy_decision else mode) or mode),
            reason=None,
            target_host=host,
            target_model=(policy_decision.target_model if policy_decision else None),
            payload_level=(policy_decision.payload_level if policy_decision else None),
            hit_rules=(policy_decision.hit_rules if policy_decision else None),
            request_meta={"operation": "PUT", "path": path},
        )
        try:
            resp = requests.put(
                url,
                headers=self._headers(),
                params=params,
                json=sanitized_body,
                timeout=self._timeout(None),
            )
        except Exception as exc:
            self._logger.error("RAGFlow PUT %s failed: %s", url, exc)
            return None

        if resp.status_code != 200:
            body_preview = ""
            try:
                body_preview = (resp.text or "")[:500]
            except Exception:
                body_preview = ""
            if body_preview:
                self._logger.error("RAGFlow PUT %s failed: HTTP %s body=%s", url, resp.status_code, body_preview)
            else:
                self._logger.error("RAGFlow PUT %s failed: HTTP %s", url, resp.status_code)
            return None

        try:
            data = resp.json()
        except Exception as exc:
            self._logger.error("RAGFlow PUT %s invalid JSON: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None

    def delete_json(
        self, path: str, *, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        blocked, reason, mode, host = self._is_egress_blocked(url=url, operation="DELETE")
        if blocked:
            self._audit_decision(
                decision="block",
                policy_mode=mode,
                reason=reason,
                target_host=host,
                request_meta={"operation": "DELETE", "path": path},
            )
            return None
        self._audit_decision(
            decision="allow",
            policy_mode=mode,
            reason=None,
            target_host=host,
            request_meta={"operation": "DELETE", "path": path},
        )
        try:
            kwargs: dict[str, Any] = {
                "headers": self._headers(),
                "params": params,
                "timeout": self._timeout(None),
            }
            # Some gateways/proxies reject or strip DELETE request bodies. Allow callers to
            # omit the body by passing `body=None`.
            if body is not None:
                kwargs["json"] = body
            resp = requests.delete(url, **kwargs)
        except Exception as exc:
            self._logger.error("RAGFlow DELETE %s failed: %s", url, exc)
            return None

        if resp.status_code != 200:
            self._logger.error("RAGFlow DELETE %s failed: HTTP %s", url, resp.status_code)
            return None

        try:
            data = resp.json()
        except Exception as exc:
            self._logger.error("RAGFlow DELETE %s invalid JSON: %s", url, exc)
            return None

        return data if isinstance(data, dict) else None

    def post_sse(
        self,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout_s: float | None = None,
        trace_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        POST an SSE endpoint and yield decoded JSON objects from `data:` lines.

        Expected payload format per line:
        - `data: {...json...}`
        """
        url = f"{self._config.base_url.rstrip('/')}{path}"
        blocked, reason, mode, host = self._is_egress_blocked(url=url, operation="SSE_POST")
        if blocked:
            self._audit_decision(
                decision="block",
                policy_mode=mode,
                reason=reason,
                target_host=host,
                request_meta={"operation": "SSE_POST", "path": path},
            )
            yield {"code": 403, "message": reason}
            return
        sanitized_body, policy_decision = self._apply_outbound_policy(body, operation="SSE_POST")
        if policy_decision is not None and not policy_decision.allowed:
            self._audit_decision(
                decision="block",
                policy_mode=str(policy_decision.policy_mode or mode),
                reason=policy_decision.blocked_reason,
                target_host=host,
                target_model=policy_decision.target_model,
                payload_level=policy_decision.payload_level,
                hit_rules=policy_decision.hit_rules,
                request_meta={"operation": "SSE_POST", "path": path},
            )
            yield {"code": 403, "message": str(policy_decision.blocked_reason or "egress_blocked_by_policy")}
            return
        self._audit_decision(
            decision="allow",
            policy_mode=str((policy_decision.policy_mode if policy_decision else mode) or mode),
            reason=None,
            target_host=host,
            target_model=(policy_decision.target_model if policy_decision else None),
            payload_level=(policy_decision.payload_level if policy_decision else None),
            hit_rules=(policy_decision.hit_rules if policy_decision else None),
            request_meta={"operation": "SSE_POST", "path": path},
        )
        trace = str(trace_id or "-").strip() or "-"
        debug_sse = str(os.getenv("RAGFLOWAUTH_DEBUG_SSE", "0")).strip() == "1"
        stream_started_at = time.perf_counter()
        line_index = 0
        event_index = 0
        connect_timeout, read_timeout = self._stream_timeout(timeout_s)

        def _preview(value: Any, max_len: int = 160) -> str:
            text = str(value or "")
            if len(text) <= max_len:
                return text
            return f"{text[:max_len]}..."

        if debug_sse:
            self._logger.warning(
                "RAGFlow SSE start trace_id=%s url=%s connect_timeout_s=%s read_timeout_s=%s",
                trace,
                url,
                connect_timeout,
                read_timeout,
            )
        else:
            self._logger.info(
                "RAGFlow SSE start trace_id=%s url=%s connect_timeout_s=%s read_timeout_s=%s",
                trace,
                url,
                connect_timeout,
                read_timeout,
            )

        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                params=params,
                json=sanitized_body,
                stream=True,
                timeout=(connect_timeout, read_timeout),
            )
        except Exception as exc:
            self._logger.error("RAGFlow SSE POST %s failed: %s", url, exc)
            yield {"code": -1, "message": str(exc)}
            return

        if resp.status_code != 200:
            self._logger.error("RAGFlow SSE POST %s failed: HTTP %s", url, resp.status_code)
            yield {"code": resp.status_code, "message": f"HTTP {resp.status_code}"}
            return

        def _decode_event_data(data_str: str, *, allow_plain_text: bool = True) -> dict[str, Any] | None:
            payload = str(data_str or "").strip()
            if not payload:
                return None
            if payload == "[DONE]":
                return {"_done": True}

            obj: Any
            try:
                obj = json.loads(payload)
            except Exception:
                try:
                    obj = ast.literal_eval(payload)
                except Exception:
                    obj = payload if allow_plain_text else None

            if obj is None:
                return None

            normalized = self._normalize_sse_event(obj) if allow_plain_text else self._normalize_sse_event_strict(obj)
            if isinstance(normalized, dict):
                return normalized
            if allow_plain_text:
                self._logger.warning("Failed to parse SSE data: %s", payload)
            return None

        event_data_lines: list[str] = []

        def _flush_event_data_lines() -> dict[str, Any] | None:
            nonlocal event_data_lines
            if not event_data_lines:
                return None
            merged = "\n".join(event_data_lines)
            if debug_sse:
                self._logger.warning(
                    "RAGFlow SSE flush trace_id=%s line_count=%s merged_len=%s merged_preview=%s",
                    trace,
                    len(event_data_lines),
                    len(merged),
                    _preview(merged),
                )
            event_data_lines = []
            return _decode_event_data(merged)

        try:
            for line in resp.iter_lines(chunk_size=1):
                if line is None:
                    continue
                line_index += 1
                try:
                    text = line.decode("utf-8", errors="replace")
                except Exception:
                    continue
                text = text.lstrip("\ufeff")
                text = text.rstrip("\r")
                if debug_sse:
                    self._logger.warning(
                        "RAGFlow SSE line trace_id=%s idx=%s len=%s preview=%s",
                        trace,
                        line_index,
                        len(text),
                        _preview(text),
                    )

                # Empty line means end of one SSE event.
                if text == "":
                    event = _flush_event_data_lines()
                    if isinstance(event, dict) and event.get("_done") is True:
                        return
                    if isinstance(event, dict):
                        yield event
                    continue

                if text.startswith(":"):
                    # SSE comment/heartbeat.
                    continue

                if text.startswith("data:"):
                    payload = text[5:].lstrip()
                    if payload.strip() == "[DONE]":
                        event = _flush_event_data_lines()
                        if isinstance(event, dict) and event.get("_done") is not True:
                            event_index += 1
                            log_fn = self._logger.warning if debug_sse else self._logger.info
                            log_fn(
                                "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                                trace,
                                event_index,
                                event.get("code"),
                                len(
                                    str(
                                        (event.get("data") or {}).get("answer")
                                        if isinstance(event.get("data"), dict)
                                        else ""
                                    )
                                ),
                                list(event.keys())[:8],
                            )
                            yield event
                        return
                    # Fast path: standalone parseable `data:` lines should be yielded immediately,
                    # even if upstream omits blank-line SSE separators.
                    if not event_data_lines:
                        single = _decode_event_data(payload, allow_plain_text=False)
                        if isinstance(single, dict):
                            event_index += 1
                            log_fn = self._logger.warning if debug_sse else self._logger.info
                            log_fn(
                                "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                                trace,
                                event_index,
                                single.get("code"),
                                len(
                                    str(
                                        (single.get("data") or {}).get("answer")
                                        if isinstance(single.get("data"), dict)
                                        else ""
                                    )
                                ),
                                list(single.keys())[:8],
                            )
                            yield single
                            continue

                    event_data_lines.append(payload)
                    merged = "\n".join(event_data_lines)
                    merged_event = _decode_event_data(merged, allow_plain_text=False)
                    if isinstance(merged_event, dict):
                        event_data_lines = []
                        event_index += 1
                        log_fn = self._logger.warning if debug_sse else self._logger.info
                        log_fn(
                            "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                            trace,
                            event_index,
                            merged_event.get("code"),
                            len(
                                str(
                                    (merged_event.get("data") or {}).get("answer")
                                    if isinstance(merged_event.get("data"), dict)
                                    else ""
                                )
                            ),
                            list(merged_event.keys())[:8],
                        )
                        yield merged_event
                    continue

                # Tolerate non-standard servers that omit repeated `data:` prefix.
                if event_data_lines:
                    event_data_lines.append(text)
                    merged = "\n".join(event_data_lines)
                    merged_event = _decode_event_data(merged, allow_plain_text=False)
                    if isinstance(merged_event, dict):
                        event_data_lines = []
                        event_index += 1
                        log_fn = self._logger.warning if debug_sse else self._logger.info
                        log_fn(
                            "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                            trace,
                            event_index,
                            merged_event.get("code"),
                            len(
                                str(
                                    (merged_event.get("data") or {}).get("answer")
                                    if isinstance(merged_event.get("data"), dict)
                                    else ""
                                )
                            ),
                            list(merged_event.keys())[:8],
                        )
                        yield merged_event

            # Flush trailing event without blank-line terminator.
            event = _flush_event_data_lines()
            if isinstance(event, dict) and event.get("_done") is not True:
                event_index += 1
                log_fn = self._logger.warning if debug_sse else self._logger.info
                log_fn(
                    "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                    trace,
                    event_index,
                    event.get("code"),
                    len(str((event.get("data") or {}).get("answer") if isinstance(event.get("data"), dict) else "")),
                    list(event.keys())[:8],
                )
                yield event
        except requests.exceptions.ChunkedEncodingError as exc:
            event = _flush_event_data_lines()
            if isinstance(event, dict) and event.get("_done") is not True:
                event_index += 1
                log_fn = self._logger.warning if debug_sse else self._logger.info
                log_fn(
                    "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                    trace,
                    event_index,
                    event.get("code"),
                    len(str((event.get("data") or {}).get("answer") if isinstance(event.get("data"), dict) else "")),
                    list(event.keys())[:8],
                )
                yield event
            self._logger.warning("RAGFlow SSE stream ended prematurely trace_id=%s url=%s: %s", trace, url, exc)
            yield {"code": -1, "message": f"upstream_stream_disconnected: {exc}"}
        except requests.exceptions.ReadTimeout as exc:
            event = _flush_event_data_lines()
            if isinstance(event, dict) and event.get("_done") is not True:
                event_index += 1
                log_fn = self._logger.warning if debug_sse else self._logger.info
                log_fn(
                    "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                    trace,
                    event_index,
                    event.get("code"),
                    len(str((event.get("data") or {}).get("answer") if isinstance(event.get("data"), dict) else "")),
                    list(event.keys())[:8],
                )
                yield event
            self._logger.warning("RAGFlow SSE read timeout trace_id=%s url=%s: %s", trace, url, exc)
            yield {"code": -1, "message": f"upstream_stream_timeout: {exc}"}
        except requests.exceptions.RequestException as exc:
            event = _flush_event_data_lines()
            if isinstance(event, dict) and event.get("_done") is not True:
                event_index += 1
                log_fn = self._logger.warning if debug_sse else self._logger.info
                log_fn(
                    "RAGFlow SSE event trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                    trace,
                    event_index,
                    event.get("code"),
                    len(str((event.get("data") or {}).get("answer") if isinstance(event.get("data"), dict) else "")),
                    list(event.keys())[:8],
                )
                yield event
            self._logger.warning("RAGFlow SSE stream request error trace_id=%s url=%s: %s", trace, url, exc)
            yield {"code": -1, "message": f"upstream_stream_error: {exc}"}
        finally:
            elapsed_ms = int((time.perf_counter() - stream_started_at) * 1000)
            log_fn = self._logger.warning if debug_sse else self._logger.info
            log_fn(
                "RAGFlow SSE end trace_id=%s url=%s lines=%s events=%s elapsed_ms=%s",
                trace,
                url,
                line_index,
                event_index,
                elapsed_ms,
            )
            try:
                resp.close()
            except Exception:
                pass

    @staticmethod
    def _extract_stream_text(payload: Any) -> str:
        def _walk(value: Any) -> str:
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                for item in value:
                    got = _walk(item)
                    if got:
                        return got
                return ""
            if isinstance(value, dict):
                for key in ("answer", "content", "text", "response"):
                    got = _walk(value.get(key))
                    if got:
                        return got
                for key in ("message", "delta", "data", "output", "result", "choices", "parts"):
                    got = _walk(value.get(key))
                    if got:
                        return got
                return ""
            return ""

        return str(_walk(payload) or "").strip()

    def _normalize_sse_event(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            if "code" in payload:
                return payload
            data_block = payload.get("data")
            if isinstance(data_block, dict):
                return {"code": 0, "data": data_block}
            text = self._extract_stream_text(payload)
            if text:
                data: dict[str, Any] = {"answer": text}
                if isinstance(payload.get("sources"), list):
                    data["sources"] = payload.get("sources")
                return {"code": 0, "data": data}
            return payload if payload else None
        if isinstance(payload, list):
            text = self._extract_stream_text(payload)
            if text:
                return {"code": 0, "data": {"answer": text}}
            return None
        if isinstance(payload, str):
            text = str(payload or "").strip()
            if text:
                return {"code": 0, "data": {"answer": text}}
            return None
        return None

    def _normalize_sse_event_strict(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            if "code" in payload:
                return payload
            data_block = payload.get("data")
            if isinstance(data_block, dict):
                return {"code": 0, "data": data_block}
            text = self._extract_stream_text(payload)
            if text:
                data: dict[str, Any] = {"answer": text}
                if isinstance(payload.get("sources"), list):
                    data["sources"] = payload.get("sources")
                return {"code": 0, "data": data}
            return None
        if isinstance(payload, list):
            text = self._extract_stream_text(payload)
            if text:
                return {"code": 0, "data": {"answer": text}}
            return None
        # strict mode intentionally does not accept raw strings
        return None

    def coerce_list(self, value: Any, *, context: str) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        self._logger.error("Unexpected %s response type: %s", context, type(value).__name__)
        return []

    def get_list(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        context: str,
        data_field: str = "data",
        ok_code: int = 0,
    ) -> list[dict[str, Any]]:
        payload = self.get_json(path, params=params)
        if not payload:
            return []
        if payload.get("code") != ok_code:
            self._logger.error("RAGFlow %s failed: %s", context, payload.get("message"))
            return []
        return self.coerce_list(payload.get(data_field, []), context=context)
