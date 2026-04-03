from __future__ import annotations

import json
from typing import Any

import requests

DEFAULT_API_BASE = "https://api.dingtalk.com"
DEFAULT_OAPI_BASE = "https://oapi.dingtalk.com"
DEFAULT_TIMEOUT_SECONDS = 30


def _ensure_json_response(resp: requests.Response, *, error_prefix: str) -> dict[str, Any]:
    if resp.status_code >= 400:
        raise RuntimeError(f"{error_prefix}:http_{resp.status_code}:{resp.text}")
    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{error_prefix}:invalid_json:{exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{error_prefix}:invalid_json_type")
    return data


def _required_config_str(config: dict[str, Any], key: str, error_code: str) -> str:
    value = str(config.get(key) or "").strip()
    if not value:
        raise RuntimeError(error_code)
    return value


def _required_agent_id(config: dict[str, Any]) -> int:
    raw = config.get("agent_id")
    if raw is None or str(raw).strip() == "":
        raise RuntimeError("dingtalk_agent_id_required")
    try:
        return int(str(raw).strip())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("dingtalk_agent_id_invalid") from exc


def _resolve_timeout_seconds(config: dict[str, Any]) -> int:
    raw = config.get("timeout_seconds")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = int(str(raw).strip())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("dingtalk_timeout_seconds_invalid") from exc
    if value <= 0:
        raise RuntimeError("dingtalk_timeout_seconds_invalid")
    return value


class DingTalkNotificationAdapter:
    def send(
        self,
        *,
        channel: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
        recipient: dict[str, Any] | None = None,
    ) -> None:
        config = channel.get("config") or {}
        app_key = _required_config_str(config, "app_key", "dingtalk_app_key_required")
        app_secret = _required_config_str(config, "app_secret", "dingtalk_app_secret_required")
        agent_id = _required_agent_id(config)
        api_base = str(config.get("api_base") or DEFAULT_API_BASE).strip() or DEFAULT_API_BASE
        oapi_base = str(config.get("oapi_base") or DEFAULT_OAPI_BASE).strip() or DEFAULT_OAPI_BASE
        timeout_seconds = _resolve_timeout_seconds(config)

        recipient_address = str((recipient or {}).get("address") or "").strip()
        if not recipient_address:
            raise RuntimeError("dingtalk_recipient_required")

        message = self._message(event_type=event_type, payload=payload, recipient=recipient)
        with requests.Session() as session:
            token = self._get_access_token(
                session=session,
                api_base=api_base,
                app_key=app_key,
                app_secret=app_secret,
                timeout_seconds=timeout_seconds,
            )
            self._send_text_work_notification(
                session=session,
                oapi_base=oapi_base,
                access_token=token,
                agent_id=agent_id,
                recipient_userid=recipient_address,
                text=message,
                timeout_seconds=timeout_seconds,
            )

    @staticmethod
    def _get_access_token(
        *,
        session: requests.Session,
        api_base: str,
        app_key: str,
        app_secret: str,
        timeout_seconds: int,
    ) -> str:
        response = session.post(
            f"{api_base.rstrip('/')}/v1.0/oauth2/accessToken",
            json={"appKey": app_key, "appSecret": app_secret},
            timeout=timeout_seconds,
        )
        data = _ensure_json_response(response, error_prefix="dingtalk_access_token_failed")
        token = str(data.get("accessToken") or "").strip()
        if not token:
            raise RuntimeError("dingtalk_access_token_failed:access_token_missing")
        return token

    @staticmethod
    def _send_text_work_notification(
        *,
        session: requests.Session,
        oapi_base: str,
        access_token: str,
        agent_id: int,
        recipient_userid: str,
        text: str,
        timeout_seconds: int,
    ) -> None:
        response = session.post(
            f"{oapi_base.rstrip('/')}/topapi/message/corpconversation/asyncsend_v2",
            params={"access_token": access_token},
            json={
                "agent_id": int(agent_id),
                "userid_list": str(recipient_userid),
                "msg": {
                    "msgtype": "text",
                    "text": {"content": text},
                },
            },
            timeout=timeout_seconds,
        )
        data = _ensure_json_response(response, error_prefix="dingtalk_send_failed")
        err_code = data.get("errcode")
        if err_code in (0, "0", None):
            return
        err_msg = str(data.get("errmsg") or "").strip()
        raise RuntimeError(f"dingtalk_send_failed:{err_code}:{err_msg}")

    @staticmethod
    def _message(*, event_type: str, payload: dict[str, Any], recipient: dict[str, Any] | None) -> str:
        approval_target = payload.get("approval_target") or {}
        return "\n".join(
            [
                f"[RagflowAuth] {event_type}",
                f"document={payload.get('filename') or payload.get('doc_id') or ''}",
                f"step={payload.get('current_step_name') or ''}",
                f"approval_path={approval_target.get('route_path') or ''}",
                f"recipient={(recipient or {}).get('username') or (recipient or {}).get('user_id') or ''}",
                json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
            ]
        )
