from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_accessible_datasets
from backend.app.core.permission_resolver import ResourceScope, assert_can_manage_kb_directory
from backend.app.dependencies import get_tenant_dependencies
from backend.models.knowledge import (
    KnowledgeDirectoryAssignmentResultEnvelope,
    KnowledgeDirectoryDeleteResultEnvelope,
    KnowledgeDirectoryNodeEnvelope,
    KnowledgeDirectoryTree,
)

router = APIRouter()


class DirectoryCreateRequest(BaseModel):
    name: str
    parent_id: str | None = None


class DirectoryUpdateRequest(BaseModel):
    name: str | None = None
    parent_id: str | None = None


class DatasetDirectoryAssignRequest(BaseModel):
    node_id: str | None = None


def _wrap_result(message: str, **extra: object) -> dict[str, dict[str, object]]:
    result: dict[str, object] = {"message": message}
    result.update(extra)
    return {"result": result}


def _require_object_payload(value: object, *, detail: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail=detail)
    return value


def _require_object_list(value: object, *, detail: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=502, detail=detail)
    for item in value:
        if not isinstance(item, dict):
            raise HTTPException(status_code=502, detail=detail)
    return value


def _require_tree_payload(value: object, *, detail: str) -> dict[str, Any]:
    payload = _require_object_payload(value, detail=detail)
    _require_object_list(payload.get("nodes"), detail=detail)
    _require_object_list(payload.get("datasets"), detail=detail)
    if not isinstance(payload.get("bindings"), dict):
        raise HTTPException(status_code=502, detail=detail)
    return payload


def _require_node_payload(value: object, *, detail: str) -> dict[str, Any]:
    return _require_object_payload(value, detail=detail)


def _require_dataset_list(value: object, *, detail: str) -> list[dict[str, Any]]:
    return _require_object_list(value, detail=detail)


def _tree_manager(deps) -> Any:
    manager = getattr(deps, "knowledge_tree_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="knowledge_tree_manager_unavailable")
    return manager


def _management_manager(deps) -> Any:
    return getattr(deps, "knowledge_management_manager", None)


def _resolve_directory_deps(request: Request, ctx: AuthContextDep, company_id: int | None):
    if company_id is None:
        return ctx.deps
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    try:
        return get_tenant_dependencies(request.app, company_id=company_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _resolve_dataset_id(deps, dataset_ref: str) -> str:
    clean_dataset_ref = str(dataset_ref or "").strip()
    if not clean_dataset_ref:
        raise HTTPException(status_code=400, detail="invalid_dataset_ref")
    normalize_dataset_id = getattr(deps.ragflow_service, "normalize_dataset_id", None)
    if not callable(normalize_dataset_id):
        raise HTTPException(status_code=500, detail="dataset_normalizer_unavailable")
    try:
        dataset_id = normalize_dataset_id(clean_dataset_ref)
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 502) or 502)
        detail = str(exc).strip() or "dataset_ref_resolution_failed"
        raise HTTPException(status_code=status, detail=detail) from exc
    clean_dataset_id = str(dataset_id or "").strip()
    if not clean_dataset_id:
        raise HTTPException(status_code=404, detail="dataset_not_found")
    return clean_dataset_id


@router.get("/directories", response_model=KnowledgeDirectoryTree)
def list_knowledge_directories(request: Request, ctx: AuthContextDep, company_id: int | None = None):
    deps = _resolve_directory_deps(request, ctx, company_id)
    management_manager = _management_manager(deps)
    if management_manager is not None:
        try:
            scope = management_manager.get_management_scope(ctx.user)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if getattr(scope, "can_manage", False):
            return _require_tree_payload(
                management_manager.list_visible_tree(ctx.user),
                detail="knowledge_directory_tree_invalid_payload",
            )
    if not ctx.snapshot.can_view_kb_config and ctx.snapshot.kb_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="no_kb_config_view_permission")
    manager = _tree_manager(deps)
    if ctx.snapshot.is_admin:
        raw_datasets = deps.ragflow_service.list_all_datasets() if hasattr(deps.ragflow_service, "list_all_datasets") else deps.ragflow_service.list_datasets()
        datasets = _require_dataset_list(raw_datasets, detail="knowledge_directory_dataset_list_invalid_payload")
        tree = manager.snapshot(datasets, prune_unknown=True)
        return _require_tree_payload(tree, detail="knowledge_directory_tree_invalid_payload")
    datasets = _require_dataset_list(
        list_accessible_datasets(deps, ctx.snapshot),
        detail="knowledge_directory_dataset_list_invalid_payload",
    )
    tree = manager.snapshot(datasets, prune_unknown=False)
    trim_fn = getattr(manager, "trim_tree_for_non_admin", None)
    if callable(trim_fn):
        tree = trim_fn(tree)
    return _require_tree_payload(tree, detail="knowledge_directory_tree_invalid_payload")


@router.post("/directories", response_model=KnowledgeDirectoryNodeEnvelope)
def create_knowledge_directory(
    request: Request,
    payload: DirectoryCreateRequest,
    ctx: AuthContextDep,
    company_id: int | None = None,
):
    deps = _resolve_directory_deps(request, ctx, company_id)
    management_manager = _management_manager(deps)
    manager = management_manager or _tree_manager(deps)
    try:
        if management_manager is not None:
            node = manager.create_directory(
                user=ctx.user,
                name=payload.name,
                parent_id=payload.parent_id,
                created_by=ctx.payload.sub,
            )
        else:
            assert_can_manage_kb_directory(ctx.snapshot)
            node = manager.create_node(name=payload.name, parent_id=payload.parent_id, created_by=ctx.payload.sub)
        node = _require_node_payload(node, detail="knowledge_directory_node_invalid_payload")
        return {"node": node}
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.put("/directories/{node_id}", response_model=KnowledgeDirectoryNodeEnvelope)
def update_knowledge_directory(node_id: str, payload: DirectoryUpdateRequest, ctx: AuthContextDep):
    fields_set = set(getattr(payload, "model_fields_set", set()) or set())
    if not fields_set:
        raise HTTPException(status_code=400, detail="missing_updates")
    updates: dict[str, Any] = {}
    if "name" in fields_set:
        updates["name"] = payload.name
    if "parent_id" in fields_set:
        updates["parent_id"] = payload.parent_id
    management_manager = _management_manager(ctx.deps)
    manager = management_manager or _tree_manager(ctx.deps)
    try:
        if management_manager is not None:
            node = manager.update_directory(user=ctx.user, node_id=node_id, payload=updates)
        else:
            assert_can_manage_kb_directory(ctx.snapshot)
            node = manager.update_node(node_id=node_id, payload=updates)
        node = _require_node_payload(node, detail="knowledge_directory_node_invalid_payload")
        return {"node": node}
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.delete("/directories/{node_id}", response_model=KnowledgeDirectoryDeleteResultEnvelope)
def delete_knowledge_directory(node_id: str, ctx: AuthContextDep):
    management_manager = _management_manager(ctx.deps)
    manager = management_manager or _tree_manager(ctx.deps)
    try:
        if management_manager is not None:
            ok = manager.delete_directory(user=ctx.user, node_id=node_id)
        else:
            assert_can_manage_kb_directory(ctx.snapshot)
            ok = manager.delete_node(node_id)
        if not ok:
            raise HTTPException(status_code=404, detail="node_not_found")
        return _wrap_result("knowledge_directory_deleted", node_id=node_id)
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.put("/directories/datasets/{dataset_ref}/node", response_model=KnowledgeDirectoryAssignmentResultEnvelope)
def assign_dataset_directory(dataset_ref: str, payload: DatasetDirectoryAssignRequest, ctx: AuthContextDep):
    dataset_id = _resolve_dataset_id(ctx.deps, dataset_ref)
    management_manager = _management_manager(ctx.deps)
    manager = management_manager or _tree_manager(ctx.deps)
    try:
        if management_manager is not None:
            assignment = manager.assign_dataset(
                user=ctx.user,
                dataset_ref=dataset_id,
                node_id=payload.node_id,
            )
            if not isinstance(assignment, tuple) or len(assignment) != 2:
                raise HTTPException(status_code=502, detail="knowledge_directory_assignment_invalid_payload")
            assigned_dataset_id, assigned_node_id = assignment
            if not isinstance(assigned_dataset_id, str) or not assigned_dataset_id.strip():
                raise HTTPException(status_code=502, detail="knowledge_directory_assignment_invalid_payload")
            if assigned_node_id is not None and not isinstance(assigned_node_id, str):
                raise HTTPException(status_code=502, detail="knowledge_directory_assignment_invalid_payload")
            return _wrap_result(
                "knowledge_dataset_directory_assigned",
                dataset_id=assigned_dataset_id,
                node_id=assigned_node_id,
            )
        assert_can_manage_kb_directory(ctx.snapshot)
        manager.assign_dataset(dataset_id=dataset_id, node_id=payload.node_id)
        return _wrap_result(
            "knowledge_dataset_directory_assigned",
            dataset_id=dataset_id,
            node_id=payload.node_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc
