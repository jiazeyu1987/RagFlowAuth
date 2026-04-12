from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError

from backend.app.core.authz import AuthContextDep
from backend.app.core.pydantic_compat import model_dump, model_validate
from backend.app.core.permission_resolver import ResourceScope, normalize_accessible_chat_ids
from backend.models.auth import ResultEnvelope
from backend.models.search_config import SearchConfigEnvelope, SearchConfigListEnvelope


router = APIRouter()
logger = logging.getLogger(__name__)


class SearchConfigBody(BaseModel):
    name: Any = None
    config: Any = None

    model_config = ConfigDict(extra="allow")


def _wrap_result(message: str, **extra: object) -> dict[str, dict[str, object]]:
    result: dict[str, object] = {"message": message}
    result.update(extra)
    return {"result": result}


def _require_config_item(value: object, *, detail: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail=detail)
    return value


def _require_config_list(value: object, *, detail: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=502, detail=detail)
    for item in value:
        if not isinstance(item, dict):
            raise HTTPException(status_code=502, detail=detail)
    return value


def _assert_admin(ctx: AuthContextDep) -> None:
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")


def _assert_agent_access(ctx: AuthContextDep, agent_id: str) -> None:
    snapshot = ctx.snapshot
    if snapshot.chat_scope == ResourceScope.ALL:
        return
    if snapshot.chat_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="no_chat_permission")
    allowed_raw_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
    if agent_id not in allowed_raw_ids:
        raise HTTPException(status_code=403, detail="no_chat_permission")


@router.get("/search/configs", response_model=SearchConfigListEnvelope)
async def list_search_configs(ctx: AuthContextDep):
    # Read is allowed for any authenticated user (same as other "config panels").
    snapshot = ctx.snapshot
    items = ctx.deps.ragflow_chat_service.list_agents(page_size=1000)
    items = _require_config_list(items, detail="config_list_invalid_payload")

    if not snapshot.is_admin:
        if snapshot.chat_scope == ResourceScope.NONE:
            items = []
        else:
            allowed_raw_ids = normalize_accessible_chat_ids(snapshot.chat_ids)
            items = [x for x in items if isinstance(x, dict) and x.get("id") in allowed_raw_ids]

    configs = []
    for x in items:
        if not isinstance(x, dict) or not x.get("id"):
            continue
        configs.append(
            {
                "id": x.get("id"),
                "name": x.get("title") or x.get("name") or x.get("id"),
                "config": {},
                "created_at_ms": x.get("create_time"),
                "updated_at_ms": x.get("update_time"),
            }
        )

    return {"configs": configs, "count": len(configs)}


@router.get("/search/configs/{config_id}", response_model=SearchConfigEnvelope)
async def get_search_config(config_id: str, ctx: AuthContextDep):
    _assert_agent_access(ctx, config_id)

    item = ctx.deps.ragflow_chat_service.get_agent(config_id)
    if not item:
        raise HTTPException(status_code=404, detail="config_not_found")
    item = _require_config_item(item, detail="config_invalid_payload")
    return {
        "config": {
            "id": item.get("id"),
            "name": item.get("title") or item.get("name") or item.get("id"),
            "config": item,
            "created_at_ms": item.get("create_time"),
            "updated_at_ms": item.get("update_time"),
        }
    }


@router.post("/search/configs", response_model=SearchConfigEnvelope)
async def create_search_config(
    ctx: AuthContextDep,
    body: object = Body(...),
):
    _assert_admin(ctx)

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_body")
    try:
        parsed = model_validate(SearchConfigBody, body)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_body")

    data = model_dump(parsed, include_none=True)
    name = body.get("name")
    config = data.get("config")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="missing_name")
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="invalid_config")

    try:
        payload: dict[str, Any] = {"title": name.strip()}
        if isinstance(config.get("description"), str) and config.get("description").strip():
            payload["description"] = str(config.get("description") or "").strip()
        dsl = config.get("dsl")
        if isinstance(dsl, dict):
            payload["dsl"] = dsl
        created = ctx.deps.ragflow_chat_service.create_agent(payload)
    except ValueError as e:
        code = str(e) or "config_create_failed"
        raise HTTPException(status_code=422, detail=code)
    except Exception as e:
        logger.error("[search_configs.create] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="config_create_failed")

    created = _require_config_item(created, detail="config_create_invalid_payload")
    if not created.get("id"):
        raise HTTPException(status_code=502, detail="config_create_invalid_payload")

    return {
        "config": {
            "id": created.get("id"),
            "name": created.get("title") or name.strip(),
            "config": created,
            "created_at_ms": created.get("create_time"),
            "updated_at_ms": created.get("update_time"),
        }
    }


@router.put("/search/configs/{config_id}", response_model=SearchConfigEnvelope)
async def update_search_config(
    config_id: str,
    ctx: AuthContextDep,
    updates: object = Body(...),
):
    _assert_admin(ctx)

    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="invalid_updates")
    try:
        parsed = model_validate(SearchConfigBody, updates)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_updates")

    data = model_dump(parsed, include_none=True)
    name = updates.get("name")
    config = data.get("config")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="missing_name")
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="invalid_config")

    try:
        payload: dict[str, Any] = {"title": name.strip()}
        if isinstance(config.get("description"), str) or config.get("description") is None:
            payload["description"] = str(config.get("description") or "")
        dsl = config.get("dsl")
        if isinstance(dsl, dict):
            payload["dsl"] = dsl
        updated = ctx.deps.ragflow_chat_service.update_agent(config_id, payload)
    except ValueError as e:
        code = str(e) or "config_update_failed"
        if code == "agent_not_found":
            raise HTTPException(status_code=404, detail="config_not_found")
        raise HTTPException(status_code=422, detail=code)
    except Exception as e:
        logger.error("[search_configs.update] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="config_update_failed")

    updated = _require_config_item(updated, detail="config_update_invalid_payload")
    if not updated.get("id"):
        raise HTTPException(status_code=502, detail="config_update_invalid_payload")

    return {
        "config": {
            "id": updated.get("id"),
            "name": updated.get("title") or name.strip(),
            "config": updated,
            "created_at_ms": updated.get("create_time"),
            "updated_at_ms": updated.get("update_time"),
        }
    }


@router.delete("/search/configs/{config_id}", response_model=ResultEnvelope)
async def delete_search_config(config_id: str, ctx: AuthContextDep):
    _assert_admin(ctx)
    try:
        ok = ctx.deps.ragflow_chat_service.delete_agent(config_id)
    except ValueError as e:
        code = str(e) or "config_delete_failed"
        if code == "agent_not_found":
            raise HTTPException(status_code=404, detail="config_not_found")
        raise HTTPException(status_code=422, detail=code)
    except Exception as e:
        logger.error("[search_configs.delete] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="config_delete_failed")
    if not ok:
        raise HTTPException(status_code=404, detail="config_not_found")
    return _wrap_result("search_config_deleted")
