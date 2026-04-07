from __future__ import annotations

import json
from typing import Any

import requests

from backend.services.operation_approval.types import OPERATION_TYPE_LABELS

DEFAULT_API_BASE = "https://api.dingtalk.com"
DEFAULT_OAPI_BASE = "https://oapi.dingtalk.com"
DEFAULT_TIMEOUT_SECONDS = 30

_OPERATION_APPROVAL_EVENT_LABELS = {
    "operation_approval_submitted": "审批已提交",
    "operation_approval_todo": "审批待处理",
    "operation_approval_rejected": "审批已驳回",
    "operation_approval_withdrawn": "审批已撤回",
    "operation_approval_executed": "审批已完成",
    "operation_approval_execution_failed": "审批执行失败",
}

_OPERATION_APPROVAL_ACTION_LABELS = {
    "knowledge_file_upload": "上传",
    "knowledge_file_delete": "删除",
    "knowledge_base_create": "新建知识库",
    "knowledge_base_delete": "删除知识库",
}


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
    def validate_channel(self, *, channel: dict[str, Any]) -> str:
        resolved = self._resolve_channel_config(channel)
        with requests.Session() as session:
            return self._get_access_token(
                session=session,
                api_base=resolved["api_base"],
                app_key=resolved["app_key"],
                app_secret=resolved["app_secret"],
                timeout_seconds=resolved["timeout_seconds"],
            )

    def send(
        self,
        *,
        channel: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
        recipient: dict[str, Any] | None = None,
    ) -> None:
        resolved = self._resolve_channel_config(channel)

        recipient_address = str((recipient or {}).get("address") or "").strip()
        if not recipient_address:
            raise RuntimeError("dingtalk_recipient_required")

        message = self._message(event_type=event_type, payload=payload, recipient=recipient)
        with requests.Session() as session:
            token = self._get_access_token(
                session=session,
                api_base=resolved["api_base"],
                app_key=resolved["app_key"],
                app_secret=resolved["app_secret"],
                timeout_seconds=resolved["timeout_seconds"],
            )
            self._send_text_work_notification(
                session=session,
                oapi_base=resolved["oapi_base"],
                access_token=token,
                agent_id=resolved["agent_id"],
                recipient_userid=recipient_address,
                text=message,
                timeout_seconds=resolved["timeout_seconds"],
            )

    @staticmethod
    def _resolve_channel_config(channel: dict[str, Any]) -> dict[str, Any]:
        config = channel.get("config") or {}
        return {
            "app_key": _required_config_str(config, "app_key", "dingtalk_app_key_required"),
            "app_secret": _required_config_str(config, "app_secret", "dingtalk_app_secret_required"),
            "agent_id": _required_agent_id(config),
            "api_base": str(config.get("api_base") or DEFAULT_API_BASE).strip() or DEFAULT_API_BASE,
            "oapi_base": str(config.get("oapi_base") or DEFAULT_OAPI_BASE).strip() or DEFAULT_OAPI_BASE,
            "timeout_seconds": _resolve_timeout_seconds(config),
        }

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
        if event_type.startswith("operation_approval_"):
            return DingTalkNotificationAdapter._operation_approval_message(event_type=event_type, payload=payload)
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

    @staticmethod
    def _operation_approval_message(*, event_type: str, payload: dict[str, Any]) -> str:
        lines = [DingTalkNotificationAdapter._operation_approval_summary(event_type=event_type, payload=payload)]

        target_label = str(payload.get("target_label") or "").strip()
        if target_label:
            lines.append(f"审批对象：{target_label}")

        current_step_name = str(payload.get("current_step_name") or "").strip()
        if current_step_name and event_type == "operation_approval_todo":
            lines.append(f"当前步骤：{current_step_name}")

        request_id = str(payload.get("request_id") or "").strip()
        if request_id:
            lines.append(f"申请单号：{request_id}")

        return "\n".join(lines)

    @staticmethod
    def _operation_approval_summary(*, event_type: str, payload: dict[str, Any]) -> str:
        operation_type = str(payload.get("operation_type") or "").strip()
        action_label = _OPERATION_APPROVAL_ACTION_LABELS.get(operation_type) or str(
            OPERATION_TYPE_LABELS.get(operation_type) or operation_type or "审批"
        )

        if event_type == "operation_approval_todo":
            if operation_type == "knowledge_file_upload":
                return "您在知识库有一条上传信息需要审批。"
            if operation_type == "knowledge_file_delete":
                return "您在知识库有一条删除信息需要审批。"
            return f"您在知识库有一条{action_label}信息需要审批。"

        if event_type == "operation_approval_submitted":
            return f"您的{action_label}申请已提交审批。"
        if event_type == "operation_approval_rejected":
            return f"您的{action_label}申请已被驳回。"
        if event_type == "operation_approval_withdrawn":
            return f"您的{action_label}申请已撤回。"
        if event_type == "operation_approval_executed":
            return f"您的{action_label}申请已审批通过并执行完成。"
        if event_type == "operation_approval_execution_failed":
            return f"您的{action_label}申请审批通过，但执行失败。"
        return f"您有一条{action_label}审批通知，请及时处理。"
