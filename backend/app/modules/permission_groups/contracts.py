from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def require_object_payload(value: object, *, detail: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail=detail)
    return value


def require_object_list(value: object, *, detail: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=502, detail=detail)
    for item in value:
        if not isinstance(item, dict):
            raise HTTPException(status_code=502, detail=detail)
    return value


def require_knowledge_tree(value: object, *, detail: str) -> dict[str, Any]:
    payload = require_object_payload(value, detail=detail)
    if not isinstance(payload.get("nodes"), list) or not isinstance(payload.get("datasets"), list):
        raise HTTPException(status_code=502, detail=detail)
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict):
        raise HTTPException(status_code=502, detail=detail)
    require_object_list(payload["nodes"], detail=detail)
    require_object_list(payload["datasets"], detail=detail)
    return payload


def require_folder_snapshot(value: object, *, detail: str) -> dict[str, Any]:
    payload = require_object_payload(value, detail=detail)
    folders = payload.get("folders")
    group_bindings = payload.get("group_bindings")
    root_group_count = payload.get("root_group_count")
    require_object_list(folders, detail=detail)
    if not isinstance(group_bindings, dict):
        raise HTTPException(status_code=502, detail=detail)
    if not isinstance(root_group_count, int) or isinstance(root_group_count, bool):
        raise HTTPException(status_code=502, detail=detail)
    for key, folder_id in group_bindings.items():
        if not isinstance(key, str):
            raise HTTPException(status_code=502, detail=detail)
        if folder_id is not None and not isinstance(folder_id, str):
            raise HTTPException(status_code=502, detail=detail)
    return payload


def visible_folder_ids(folder_snapshot: dict) -> set[str]:
    return {
        str(folder.get("id"))
        for folder in (folder_snapshot or {}).get("folders", [])
        if isinstance(folder, dict) and isinstance(folder.get("id"), str) and folder.get("id")
    }


def wrap_groups(groups: list[dict]) -> dict[str, list[dict]]:
    return {"groups": groups}


def wrap_group(group: dict) -> dict[str, dict]:
    return {"group": group}


def wrap_result(message: str, **extra: object) -> dict[str, dict[str, object]]:
    result: dict[str, object] = {"message": message}
    result.update(extra)
    return {"result": result}


def wrap_knowledge_bases(knowledge_bases: list[dict]) -> dict[str, list[dict]]:
    return {"knowledge_bases": knowledge_bases}


def wrap_knowledge_tree(knowledge_tree: dict) -> dict[str, dict]:
    return {"knowledge_tree": knowledge_tree}


def wrap_chats(chats: list[dict]) -> dict[str, list[dict]]:
    return {"chats": chats}


def wrap_folder_snapshot(folder_snapshot: dict) -> dict[str, dict]:
    return {"folder_snapshot": folder_snapshot}


def wrap_folder(folder: dict) -> dict[str, dict]:
    return {"folder": folder}


def raise_resource_error(action: str, exc: Exception, *, default_detail: str) -> None:
    logger.error("Failed to %s: %s", action, exc, exc_info=True)
    status_code = int(getattr(exc, "status_code", 500) or 500)
    detail = str(exc).strip() or default_detail
    raise HTTPException(status_code=status_code, detail=detail) from exc
