from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field, ValidationError

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_accessible_datasets
from backend.app.core.permdbg import permdbg
from backend.app.core.permission_resolver import allowed_dataset_ids, assert_kb_allowed
from backend.app.core.pydantic_compat import model_dump, model_validate
from backend.services.audit_helpers import actor_fields_from_ctx


router = APIRouter()
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    question: str
    dataset_ids: Optional[list[str]] = None
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=30, ge=1, le=500)
    similarity_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    top_k: int = Field(default=30, ge=1, le=200)
    keyword: bool = False
    highlight: bool = False


class DatasetCreateBody(BaseModel):
    name: Any = None

    class Config:
        extra = "allow"


class DatasetUpdateBody(BaseModel):
    name: Any = None

    class Config:
        extra = "allow"


@router.post("/search")
async def search_chunks(
    request_data: SearchRequest,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    question = str(request_data.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question_required")

    all_datasets = deps.ragflow_service.list_datasets()
    available_dataset_ids = allowed_dataset_ids(snapshot, all_datasets)

    try:
        permdbg(
            "search.request",
            user=ctx.user.username,
            role=ctx.user.role,
            kb_scope=snapshot.kb_scope,
            requested_dataset_ids=(request_data.dataset_ids or [])[:50],
            allowed_dataset_ids=available_dataset_ids[:50],
        )
    except Exception:
        pass

    if request_data.dataset_ids:
        normalize = getattr(deps.ragflow_service, "normalize_dataset_ids", None)
        requested_ids = normalize(request_data.dataset_ids) if callable(normalize) else request_data.dataset_ids
        valid_dataset_ids = [ds_id for ds_id in requested_ids if ds_id in available_dataset_ids]
        if not valid_dataset_ids:
            raise HTTPException(status_code=403, detail="dataset_not_allowed")
        dataset_ids = valid_dataset_ids
    else:
        dataset_ids = available_dataset_ids

    if not dataset_ids:
        raise HTTPException(status_code=403, detail="no_accessible_knowledge_bases")

    try:
        return deps.ragflow_chat_service.retrieve_chunks(
            question=question,
            dataset_ids=dataset_ids,
            page=request_data.page,
            page_size=request_data.page_size,
            similarity_threshold=request_data.similarity_threshold,
            top_k=request_data.top_k,
            keyword=request_data.keyword,
            highlight=request_data.highlight,
        )
    except Exception as exc:
        logger.error("[SEARCH] Error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="search_failed")


@router.get("/datasets")
async def list_available_datasets(
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    datasets = list_accessible_datasets(deps, snapshot)
    if snapshot.is_admin:
        return {"datasets": datasets, "count": len(datasets)}

    filtered = datasets
    try:
        permdbg(
            "datasets.list",
            user=ctx.user.username,
            role=ctx.user.role,
            kb_scope=snapshot.kb_scope,
            kb_refs=sorted(list(snapshot.kb_names))[:50],
            datasets=[d.get("name") for d in filtered[:50] if isinstance(d, dict)],
        )
    except Exception:
        pass
    return {"datasets": filtered, "count": len(filtered)}


@router.get("/datasets/{dataset_ref}")
async def get_dataset_detail(
    dataset_ref: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    assert_kb_allowed(snapshot, dataset_ref)

    detail = None
    try:
        detail = deps.ragflow_service.get_dataset_detail(dataset_ref)
    except Exception as exc:
        logger.error("[datasets.get] error: %s", exc, exc_info=True)
        detail = None

    if not detail:
        raise HTTPException(status_code=404, detail="dataset_not_found")

    return {"dataset": detail}


@router.put("/datasets/{dataset_ref}")
async def update_dataset_detail(
    dataset_ref: str,
    ctx: AuthContextDep,
    updates: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    assert_kb_allowed(snapshot, dataset_ref)

    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="invalid_updates")
    try:
        parsed = model_validate(DatasetUpdateBody, updates)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_updates")

    updates = model_dump(parsed, include_none=True)

    updates.pop("id", None)
    updates.pop("dataset_id", None)

    updated = None
    try:
        updated = deps.ragflow_service.update_dataset(dataset_ref, updates)
    except Exception as exc:
        logger.error("[datasets.update] error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc) or "dataset_update_failed")

    if not updated:
        raise HTTPException(status_code=500, detail="dataset_update_failed")

    audit = getattr(deps, "audit_log_store", None)
    if audit:
        try:
            audit.log_event(
                action="datasets_update",
                actor=ctx.payload.sub,
                source="ragflow",
                kb_id=str(updated.get("id") or dataset_ref),
                kb_name=str(updated.get("name") or dataset_ref),
                meta={"keys": sorted([k for k in updates.keys() if isinstance(k, str)])[:100]},
                **actor_fields_from_ctx(deps, ctx),
            )
        except Exception:
            pass

    return {"dataset": updated}


@router.post("/datasets")
async def create_dataset(
    ctx: AuthContextDep,
    body: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_body")
    try:
        parsed = model_validate(DatasetCreateBody, body)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_body")

    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="missing_name")
    name = name.strip()

    body = model_dump(parsed, include_none=True)
    body["name"] = name
    body.pop("id", None)
    body.pop("dataset_id", None)

    created = None
    try:
        created = deps.ragflow_service.create_dataset(body)
    except Exception as exc:
        logger.error("[datasets.create] error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc) or "dataset_create_failed")

    if not created:
        raise HTTPException(status_code=500, detail="dataset_create_failed")

    audit = getattr(deps, "audit_log_store", None)
    if audit:
        try:
            audit.log_event(
                action="datasets_create",
                actor=ctx.payload.sub,
                source="ragflow",
                kb_id=str(created.get("id") or ""),
                kb_name=str(created.get("name") or name),
                meta={"keys": sorted([k for k in body.keys() if isinstance(k, str)])[:100]},
                **actor_fields_from_ctx(deps, ctx),
            )
        except Exception:
            pass

    return {"dataset": created}


@router.delete("/datasets/{dataset_ref}")
async def delete_dataset(
    dataset_ref: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    assert_kb_allowed(snapshot, dataset_ref)

    try:
        deps.ragflow_service.delete_dataset_if_empty(dataset_ref)
    except ValueError as exc:
        code = str(exc) or "delete_failed"
        if code == "dataset_not_found":
            raise HTTPException(status_code=404, detail="dataset_not_found")
        if code == "dataset_not_empty":
            raise HTTPException(status_code=409, detail="dataset_not_empty")
        raise HTTPException(status_code=400, detail=code)
    except Exception as exc:
        logger.error("[datasets.delete] error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc) or "dataset_delete_failed")

    audit = getattr(deps, "audit_log_store", None)
    if audit:
        try:
            audit.log_event(
                action="datasets_delete",
                actor=ctx.payload.sub,
                source="ragflow",
                kb_id=str(dataset_ref),
                kb_name=str(dataset_ref),
                meta={},
                **actor_fields_from_ctx(deps, ctx),
            )
        except Exception:
            pass

    return {"ok": True}
