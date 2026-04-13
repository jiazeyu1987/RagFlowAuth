from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_visible_datasets
from backend.app.core.permdbg import permdbg
from backend.app.core.permission_resolver import allowed_dataset_ids, assert_kb_allowed
from backend.app.core.pydantic_compat import model_dump, model_validate
from backend.models.knowledge import DatasetEnvelope, DatasetListEnvelope
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.audit_helpers import (
    build_audit_evidence_refs,
    first_evidence_document_context,
    log_quality_audit_event,
)
from backend.models.operation_approval import OperationApprovalRequestBrief, OperationApprovalRequestEnvelope
from backend.services.knowledge_ingestion import KnowledgeIngestionError, KnowledgeIngestionManager


router = APIRouter()
logger = logging.getLogger(__name__)


def _wrap_operation_request(brief: dict) -> dict[str, dict]:
    return {"request": OperationApprovalRequestBrief(**brief).model_dump()}


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
    node_id: str | None = None

    model_config = ConfigDict(extra="allow")


class DatasetUpdateBody(BaseModel):
    name: Any = None

    model_config = ConfigDict(extra="allow")


@router.post("/search")
async def search_chunks(
    request_data: SearchRequest,
    ctx: AuthContextDep,
    request: Request,
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
        result = deps.ragflow_chat_service.retrieve_chunks(
            question=question,
            dataset_ids=dataset_ids,
            page=request_data.page,
            page_size=request_data.page_size,
            similarity_threshold=request_data.similarity_threshold,
            top_k=request_data.top_k,
            keyword=request_data.keyword,
            highlight=request_data.highlight,
        )
        chunks = result.get("chunks") if isinstance(result, dict) else []
        evidence_refs = build_audit_evidence_refs(
            chunks if isinstance(chunks, list) else [],
            default_role="search_hit",
        )
        doc_context = first_evidence_document_context(evidence_refs)
        request_id = str(getattr(getattr(request, "state", None), "request_id", "") or "").strip() or None
        log_quality_audit_event(
            deps=deps,
            ctx=ctx,
            action="global_search_execute",
            source="global_search",
            resource_type="search_request",
            resource_id=request_id,
            event_type="search",
            request_id=request_id,
            before={
                "question": question,
                "dataset_ids": list(dataset_ids),
                "page": request_data.page,
                "page_size": request_data.page_size,
                "similarity_threshold": request_data.similarity_threshold,
                "top_k": request_data.top_k,
                "keyword": request_data.keyword,
                "highlight": request_data.highlight,
            },
            after={
                "total": int(result.get("total") or 0) if isinstance(result, dict) else 0,
                "returned_chunks": len(chunks) if isinstance(chunks, list) else 0,
            },
            doc_id=doc_context["doc_id"],
            filename=doc_context["filename"],
            kb_id=doc_context["kb_id"],
            kb_dataset_id=doc_context["kb_dataset_id"],
            kb_name=doc_context["kb_name"],
            evidence_refs=evidence_refs,
            meta={
                "query": question,
                "dataset_ids": list(dataset_ids),
                "dataset_count": len(dataset_ids),
                "result_total": int(result.get("total") or 0) if isinstance(result, dict) else 0,
                "returned_chunks": len(chunks) if isinstance(chunks, list) else 0,
                "evidence_count": len(evidence_refs),
            },
        )
        return result
    except Exception as exc:
        logger.error("[SEARCH] Error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="search_failed")


@router.get("/datasets", response_model=DatasetListEnvelope)
async def list_available_datasets(
    ctx: AuthContextDep,
):
    datasets = list_visible_datasets(ctx.deps, ctx.snapshot, ctx.user)
    if ctx.snapshot.is_admin or str(getattr(ctx.user, "role", "") or "") == "sub_admin":
        return {"datasets": datasets, "count": len(datasets)}

    try:
        permdbg(
            "datasets.list",
            user=ctx.user.username,
            role=ctx.user.role,
            kb_scope=ctx.snapshot.kb_scope,
            kb_refs=sorted(list(ctx.snapshot.kb_names))[:50],
            datasets=[d.get("name") for d in datasets[:50] if isinstance(d, dict)],
        )
    except Exception:
        pass
    return {"datasets": datasets, "count": len(datasets)}


@router.get("/datasets/{dataset_ref}", response_model=DatasetEnvelope)
async def get_dataset_detail(
    dataset_ref: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    management_manager = getattr(deps, "knowledge_management_manager", None)

    if str(getattr(ctx.user, "role", "") or "") == "sub_admin" and management_manager is not None:
        try:
            management_manager.assert_dataset_manageable(ctx.user, dataset_ref)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc
    else:
        assert_kb_allowed(snapshot, dataset_ref)

    try:
        detail = deps.ragflow_service.get_dataset_detail(dataset_ref)
    except Exception as exc:
        logger.error("[datasets.get] error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=int(getattr(exc, "status_code", 502) or 502),
            detail=str(exc).strip() or "dataset_detail_failed",
        ) from exc

    if not detail:
        raise HTTPException(status_code=404, detail="dataset_not_found")
    if not isinstance(detail, dict):
        raise HTTPException(status_code=502, detail="dataset_invalid_payload")

    return {"dataset": detail}


@router.put("/datasets/{dataset_ref}", response_model=DatasetEnvelope)
async def update_dataset_detail(
    dataset_ref: str,
    ctx: AuthContextDep,
    updates: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    management_manager = getattr(deps, "knowledge_management_manager", None)

    if snapshot.is_admin:
        assert_kb_allowed(snapshot, dataset_ref)
    elif str(getattr(ctx.user, "role", "") or "") == "sub_admin" and management_manager is not None:
        try:
            management_manager.assert_dataset_manageable(ctx.user, dataset_ref)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=403, detail="admin_required")

    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="invalid_updates")
    try:
        parsed = model_validate(DatasetUpdateBody, updates)
    except ValidationError:
        raise HTTPException(status_code=400, detail="invalid_updates")

    updates = model_dump(parsed, include_none=True)

    updates.pop("id", None)
    updates.pop("dataset_id", None)

    if snapshot.is_admin or management_manager is None:
        updated = None
        try:
            updated = deps.ragflow_service.update_dataset(dataset_ref, updates)
        except Exception as exc:
            logger.error("[datasets.update] error: %s", exc, exc_info=True)
            raise HTTPException(status_code=502, detail=str(exc) or "dataset_update_failed")
        if not updated:
            raise HTTPException(status_code=500, detail="dataset_update_failed")
    else:
        try:
            updated = management_manager.update_dataset(user=ctx.user, dataset_ref=dataset_ref, updates=updates)
        except Exception as exc:
            raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc

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


@router.post("/datasets", response_model=DatasetEnvelope)
async def create_dataset(
    ctx: AuthContextDep,
    body: object = Body(...),
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    management_manager = getattr(deps, "knowledge_management_manager", None)

    if not snapshot.is_admin and str(getattr(ctx.user, "role", "") or "") != "sub_admin":
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
    if management_manager is None:
        raise HTTPException(status_code=500, detail="knowledge_management_manager_unavailable")
    try:
        created = management_manager.create_dataset(user=ctx.user, payload=body)
    except Exception as exc:
        raise HTTPException(
            status_code=int(getattr(exc, "status_code", 400) or 400),
            detail=getattr(exc, "code", None) or str(exc) or "dataset_create_failed",
        ) from exc

    try:
        KnowledgeIngestionManager(deps).create_dataset_readme(
            dataset_id=str(created.get("id") or "").strip(),
            dataset_name=str(created.get("name") or name).strip(),
            uploaded_by=ctx.payload.sub,
        )
    except KnowledgeIngestionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc).strip() or "dataset_readme_create_failed",
        ) from exc

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


@router.delete("/datasets/{dataset_ref}", response_model=OperationApprovalRequestEnvelope, status_code=202)
async def delete_dataset(
    dataset_ref: str,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    management_manager = getattr(deps, "knowledge_management_manager", None)

    if not snapshot.is_admin and str(getattr(ctx.user, "role", "") or "") != "sub_admin":
        raise HTTPException(status_code=403, detail="admin_required")
    service = getattr(deps, "operation_approval_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
    try:
        brief = await service.create_request(
            operation_type="knowledge_base_delete",
            ctx=ctx,
            dataset_ref=dataset_ref,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=int(getattr(exc, "status_code", 400) or 400),
            detail=getattr(exc, "code", None) or str(exc) or "operation_approval_create_failed",
        ) from exc
    return _wrap_operation_request(brief)
