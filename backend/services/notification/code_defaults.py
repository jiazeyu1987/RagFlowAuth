from __future__ import annotations

from typing import Any

CODE_OWNED_DINGTALK_CHANNEL_ID = "dingtalk-main"

CODE_OWNED_DINGTALK_CHANNEL = {
    "channel_id": CODE_OWNED_DINGTALK_CHANNEL_ID,
    "channel_type": "dingtalk",
    "name": "钉钉工作通知",
    "enabled": True,
    "config": {
        "app_key": "dingidnt7v7zbm5tqzyn",
        "app_secret": "gi-v0YEkV_SCwXo9vGvYgBJzEbQ4wS4WUXDwA7ZkqMuNflFu0JfdFW1TeJIxcOjC",
        "agent_id": "4432005762",
        "api_base": "https://api.dingtalk.com",
        "oapi_base": "https://oapi.dingtalk.com",
        "timeout_seconds": 30,
    },
}

CODE_OWNED_EVENT_RULES = {
    "operation_approval_todo": ["in_app", "dingtalk"],
}


def build_code_owned_dingtalk_channel(existing_channel: dict[str, Any] | None) -> dict[str, Any]:
    existing_config = (existing_channel or {}).get("config") or {}
    recipient_map = existing_config.get("recipient_map")
    if not isinstance(recipient_map, dict):
        recipient_map = {}
    recipient_directory = existing_config.get("recipient_directory")
    if not isinstance(recipient_directory, dict):
        recipient_directory = {}
    config = dict(CODE_OWNED_DINGTALK_CHANNEL["config"])
    config["recipient_map"] = dict(recipient_map)
    config["recipient_directory"] = dict(recipient_directory)
    return {
        "channel_id": CODE_OWNED_DINGTALK_CHANNEL["channel_id"],
        "channel_type": CODE_OWNED_DINGTALK_CHANNEL["channel_type"],
        "name": CODE_OWNED_DINGTALK_CHANNEL["name"],
        "enabled": CODE_OWNED_DINGTALK_CHANNEL["enabled"],
        "config": config,
    }
