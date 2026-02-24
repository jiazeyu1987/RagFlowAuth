from fastapi import APIRouter, HTTPException, Body
from typing import Any, Optional
import logging
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_accessible_datasets
from backend.app.core.permdbg import permdbg
from backend.app.core.permission_resolver import ResourceScope, allowed_dataset_ids, filter_datasets_by_name, assert_kb_allowed
from backend.services.audit_helpers import actor_fields_from_ctx


router = APIRouter()
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    """Search request model"""
    question: str
    dataset_ids: Optional[list[str]] = None
    page: int = 1
    page_size: int = 30
    similarity_threshold: float = 0.2
    top_k: int = 30
    keyword: bool = False
    highlight: bool = False


@router.post("/search")
async def search_chunks(
    request_data: SearchRequest,
    ctx: AuthContextDep,
):
    """
    在知识库中检索文本块（chunks）（基于权限组）

    权限规则：
    - 管理员：可以检索所有知识库
    - 其他角色：只能检索权限组中配置的知识库
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

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

    # 如果指定了dataset_ids，验证用户是否有权限
    if request_data.dataset_ids:
        normalize = getattr(deps.ragflow_service, "normalize_dataset_ids", None)
        requested_ids = normalize(request_data.dataset_ids) if callable(normalize) else request_data.dataset_ids
        valid_dataset_ids = [ds_id for ds_id in requested_ids if ds_id in available_dataset_ids]
        if not valid_dataset_ids:
            raise HTTPException(status_code=403, detail="您没有权限访问指定的知识库")
        dataset_ids = valid_dataset_ids
    else:
        dataset_ids = available_dataset_ids

    if not dataset_ids:
        raise HTTPException(status_code=403, detail="no_accessible_knowledge_bases")

    # 调用检索服务
    try:
        result = deps.ragflow_chat_service.retrieve_chunks(
            question=request_data.question,
            dataset_ids=dataset_ids,
            page=request_data.page,
            page_size=request_data.page_size,
            similarity_threshold=request_data.similarity_threshold,
            top_k=request_data.top_k,
            keyword=request_data.keyword,
            highlight=request_data.highlight
        )

        return result
    except Exception as e:
        logger.error(f"[SEARCH] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/datasets")
async def list_available_datasets(
    ctx: AuthContextDep,
):
    """
    获取用户可用的知识库列表（基于权限组）

    权限规则：
    - 管理员：可以看到所有知识库
    - 其他角色：根据权限组的accessible_kbs配置
    """
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
    except Exception as e:
        logger.error("[datasets.get] error: %s", e, exc_info=True)
        detail = None

    if not detail:
        raise HTTPException(status_code=404, detail="dataset_not_found")

    return {"dataset": detail}


@router.put("/datasets/{dataset_ref}")
async def update_dataset_detail(
    dataset_ref: str,
    ctx: AuthContextDep,
    updates: dict[str, Any] = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    assert_kb_allowed(snapshot, dataset_ref)

    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="invalid_updates")

    # Guardrails: dataset id is controlled by the path, not the body.
    updates.pop("id", None)
    updates.pop("dataset_id", None)

    updated = None
    try:
        updated = deps.ragflow_service.update_dataset(dataset_ref, updates)
    except Exception as e:
        logger.error("[datasets.update] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "dataset_update_failed")

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
    body: dict[str, Any] = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_body")

    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="missing_name")
    name = name.strip()

    # Guardrails: avoid accidental overrides.
    body = dict(body)
    body["name"] = name
    body.pop("id", None)
    body.pop("dataset_id", None)

    created = None
    try:
        created = deps.ragflow_service.create_dataset(body)
    except Exception as e:
        logger.error("[datasets.create] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "dataset_create_failed")

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
    except ValueError as e:
        code = str(e) or "delete_failed"
        if code == "dataset_not_found":
            raise HTTPException(status_code=404, detail="dataset_not_found")
        if code == "dataset_not_empty":
            raise HTTPException(status_code=409, detail="dataset_not_empty")
        raise HTTPException(status_code=400, detail=code)
    except Exception as e:
        logger.error("[datasets.delete] error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=str(e) or "dataset_delete_failed")

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
