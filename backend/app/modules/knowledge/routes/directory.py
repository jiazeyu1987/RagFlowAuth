from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
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


def _trim_tree_for_non_admin(tree: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in (tree.get("nodes") or []) if isinstance(node, dict)]
    datasets = [ds for ds in (tree.get("datasets") or []) if isinstance(ds, dict)]
    node_by_id = {str(node.get("id")): node for node in nodes if isinstance(node.get("id"), str)}

    keep_node_ids: set[str] = set()
    for ds in datasets:
        node_id = ds.get("node_id")
        cur = str(node_id) if isinstance(node_id, str) and node_id else None
        guard: set[str] = set()
        while cur and cur not in guard:
            guard.add(cur)
            keep_node_ids.add(cur)
            node = node_by_id.get(cur)
            if not node:
                break
            parent_id = node.get("parent_id")
            cur = str(parent_id) if isinstance(parent_id, str) and parent_id else None

    return {
        "nodes": [node for node in nodes if str(node.get("id") or "") in keep_node_ids],
        "datasets": datasets,
        "bindings": {
            str(ds.get("id")): ds.get("node_id")
            for ds in datasets
            if isinstance(ds.get("id"), str) and ds.get("id")
        },
    }


@router.get("/directories")
async def list_knowledge_directories(ctx: AuthContextDep):
    deps = ctx.deps
    if ctx.snapshot.is_admin:
        datasets = deps.ragflow_service.list_all_datasets() if hasattr(deps.ragflow_service, "list_all_datasets") else deps.ragflow_service.list_datasets()
        tree = deps.knowledge_directory_manager.snapshot(datasets or [], prune_unknown=True)
        return tree
    datasets = list_accessible_datasets(deps, ctx.snapshot)
    tree = deps.knowledge_directory_manager.snapshot(datasets or [], prune_unknown=False)
    return _trim_tree_for_non_admin(tree)


@router.post("/directories")
async def create_knowledge_directory(payload: DirectoryCreateRequest, ctx: AuthContextDep):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    try:
        node = ctx.deps.knowledge_directory_store.create_node(
            payload.name,
            payload.parent_id,
            created_by=ctx.payload.sub,
        )
        return {"node": {"id": node["node_id"], "name": node["name"], "parent_id": node.get("parent_id")}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/directories/{node_id}")
async def update_knowledge_directory(node_id: str, payload: DirectoryUpdateRequest, ctx: AuthContextDep):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    fields_set = set(getattr(payload, "model_fields_set", set()) or set())
    if not fields_set:
        raise HTTPException(status_code=400, detail="missing_updates")
    updates: dict[str, Any] = {}
    if "name" in fields_set:
        updates["name"] = payload.name
    if "parent_id" in fields_set:
        updates["parent_id"] = payload.parent_id
    try:
        node = ctx.deps.knowledge_directory_store.update_node(
            node_id,
            **updates,
        )
        return {"node": {"id": node["node_id"], "name": node["name"], "parent_id": node.get("parent_id")}}
    except ValueError as exc:
        code = str(exc)
        status = 404 if code == "node_not_found" else 400
        raise HTTPException(status_code=status, detail=code) from exc


@router.delete("/directories/{node_id}")
async def delete_knowledge_directory(node_id: str, ctx: AuthContextDep):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    try:
        ok = ctx.deps.knowledge_directory_store.delete_node(node_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="node_not_found")
    return {"ok": True}


@router.put("/directories/datasets/{dataset_ref}/node")
async def assign_dataset_directory(dataset_ref: str, payload: DatasetDirectoryAssignRequest, ctx: AuthContextDep):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
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
    try:
        ctx.deps.knowledge_directory_store.assign_dataset(dataset_id, payload.node_id)
        return {"ok": True, "dataset_id": dataset_id, "node_id": payload.node_id}
    except ValueError as exc:
        code = str(exc)
        status = 404 if code in {"node_not_found"} else 400
        raise HTTPException(status_code=status, detail=code) from exc
