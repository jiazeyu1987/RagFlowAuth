from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.datasets import list_accessible_datasets
from backend.app.core.permission_resolver import ResourceScope, assert_can_manage_kb_directory
from backend.app.dependencies import get_tenant_dependencies

router = APIRouter()


class DirectoryCreateRequest(BaseModel):
    name: str
    parent_id: str | None = None


class DirectoryUpdateRequest(BaseModel):
    name: str | None = None
    parent_id: str | None = None


class DatasetDirectoryAssignRequest(BaseModel):
    node_id: str | None = None


def _tree_manager(deps) -> Any:
    return getattr(deps, "knowledge_tree_manager", None) or getattr(deps, "knowledge_directory_manager")


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


@router.get("/directories")
def list_knowledge_directories(request: Request, ctx: AuthContextDep, company_id: int | None = None):
    deps = _resolve_directory_deps(request, ctx, company_id)
    management_manager = _management_manager(deps)
    if management_manager is not None:
        try:
            scope = management_manager.get_management_scope(ctx.user)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if getattr(scope, "can_manage", False):
            return management_manager.list_visible_tree(ctx.user)
    if not ctx.snapshot.can_view_kb_config and ctx.snapshot.kb_scope == ResourceScope.NONE:
        raise HTTPException(status_code=403, detail="no_kb_config_view_permission")
    manager = _tree_manager(deps)
    if ctx.snapshot.is_admin:
        datasets = deps.ragflow_service.list_all_datasets() if hasattr(deps.ragflow_service, "list_all_datasets") else deps.ragflow_service.list_datasets()
        tree = manager.snapshot(datasets or [], prune_unknown=True)
        return tree
    datasets = list_accessible_datasets(deps, ctx.snapshot)
    tree = manager.snapshot(datasets or [], prune_unknown=False)
    trim_fn = getattr(manager, "trim_tree_for_non_admin", None)
    return trim_fn(tree) if callable(trim_fn) else tree


@router.post("/directories")
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
        return {"node": node}
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.put("/directories/{node_id}")
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
        return {"node": node}
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.delete("/directories/{node_id}")
def delete_knowledge_directory(node_id: str, ctx: AuthContextDep):
    management_manager = _management_manager(ctx.deps)
    manager = management_manager or _tree_manager(ctx.deps)
    try:
        if management_manager is not None:
            ok = manager.delete_directory(user=ctx.user, node_id=node_id)
        else:
            assert_can_manage_kb_directory(ctx.snapshot)
            ok = manager.delete_node(node_id)
        return {"ok": bool(ok)}
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.put("/directories/datasets/{dataset_ref}/node")
def assign_dataset_directory(dataset_ref: str, payload: DatasetDirectoryAssignRequest, ctx: AuthContextDep):
    normalize_dataset_id = getattr(ctx.deps.ragflow_service, "normalize_dataset_id", None)
    dataset_id = normalize_dataset_id(dataset_ref) if callable(normalize_dataset_id) else None
    if not dataset_id and isinstance(dataset_ref, str) and dataset_ref:
        try:
            list_all = getattr(ctx.deps.ragflow_service, "list_all_datasets", None)
            datasets = list_all() if callable(list_all) else (ctx.deps.ragflow_service.list_datasets() or [])
            for ds in datasets:
                if not isinstance(ds, dict):
                    continue
                ds_id = ds.get("id")
                ds_name = ds.get("name")
                if ds_id == dataset_ref or ds_name == dataset_ref:
                    dataset_id = ds_id or dataset_id
                    break
        except Exception:
            pass
    if not dataset_id:
        dataset_id = dataset_ref if isinstance(dataset_ref, str) and dataset_ref else None
    if not dataset_id:
        raise HTTPException(status_code=400, detail="invalid_dataset_ref")
    management_manager = _management_manager(ctx.deps)
    manager = management_manager or _tree_manager(ctx.deps)
    try:
        if management_manager is not None:
            dataset_id, node_id = manager.assign_dataset(user=ctx.user, dataset_ref=dataset_id, node_id=payload.node_id)
            return {"ok": True, "dataset_id": dataset_id, "node_id": node_id}
        assert_can_manage_kb_directory(ctx.snapshot)
        manager.assign_dataset(dataset_id=dataset_id, node_id=payload.node_id)
        return {"ok": True, "dataset_id": dataset_id, "node_id": payload.node_id}
    except HTTPException:
        raise
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc
