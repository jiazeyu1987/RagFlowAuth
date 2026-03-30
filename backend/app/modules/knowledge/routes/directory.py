from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_can_manage_kb_directory, assert_can_view_kb_config
from backend.app.core.datasets import list_accessible_datasets

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


@router.get("/directories")
def list_knowledge_directories(ctx: AuthContextDep):
    assert_can_view_kb_config(ctx.snapshot)
    deps = ctx.deps
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
def create_knowledge_directory(payload: DirectoryCreateRequest, ctx: AuthContextDep):
    assert_can_manage_kb_directory(ctx.snapshot)
    manager = _tree_manager(ctx.deps)
    try:
        node = manager.create_node(name=payload.name, parent_id=payload.parent_id, created_by=ctx.payload.sub)
        return {"node": node}
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.put("/directories/{node_id}")
def update_knowledge_directory(node_id: str, payload: DirectoryUpdateRequest, ctx: AuthContextDep):
    assert_can_manage_kb_directory(ctx.snapshot)
    fields_set = set(getattr(payload, "model_fields_set", set()) or set())
    if not fields_set:
        raise HTTPException(status_code=400, detail="missing_updates")
    updates: dict[str, Any] = {}
    if "name" in fields_set:
        updates["name"] = payload.name
    if "parent_id" in fields_set:
        updates["parent_id"] = payload.parent_id
    manager = _tree_manager(ctx.deps)
    try:
        node = manager.update_node(node_id=node_id, payload=updates)
        return {"node": node}
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.delete("/directories/{node_id}")
def delete_knowledge_directory(node_id: str, ctx: AuthContextDep):
    assert_can_manage_kb_directory(ctx.snapshot)
    manager = _tree_manager(ctx.deps)
    try:
        ok = manager.delete_node(node_id)
        return {"ok": bool(ok)}
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.put("/directories/datasets/{dataset_ref}/node")
def assign_dataset_directory(dataset_ref: str, payload: DatasetDirectoryAssignRequest, ctx: AuthContextDep):
    assert_can_manage_kb_directory(ctx.snapshot)
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
    manager = _tree_manager(ctx.deps)
    try:
        manager.assign_dataset(dataset_id=dataset_id, node_id=payload.node_id)
        return {"ok": True, "dataset_id": dataset_id, "node_id": payload.node_id}
    except Exception as exc:
        status = int(getattr(exc, "status_code", 400) or 400)
        raise HTTPException(status_code=status, detail=str(exc)) from exc
