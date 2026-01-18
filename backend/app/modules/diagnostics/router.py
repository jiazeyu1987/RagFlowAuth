from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.permission_resolver import ResourceScope
from backend.services.ragflow_config import is_placeholder_api_key


router = APIRouter()


@router.get("/diagnostics/permissions")
async def permissions_diagnostics(ctx: AuthContextDep):
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot

    ragflow = deps.ragflow_service
    kb_ids = []
    kb_names = []
    try:
        if snapshot.kb_scope == ResourceScope.ALL:
            datasets = ragflow.list_all_datasets() if hasattr(ragflow, "list_all_datasets") else ragflow.list_datasets()
            kb_ids = [ds.get("id") for ds in datasets or [] if isinstance(ds, dict) and ds.get("id")]
            kb_names = [ds.get("name") for ds in datasets or [] if isinstance(ds, dict) and ds.get("name")]
        else:
            kb_ids = ragflow.normalize_dataset_ids(list(snapshot.kb_names)) if hasattr(ragflow, "normalize_dataset_ids") else []
            kb_names = (
                ragflow.resolve_dataset_names(list(snapshot.kb_names)) if hasattr(ragflow, "resolve_dataset_names") else list(snapshot.kb_names)
            )
    except Exception:
        kb_ids = []
        kb_names = []

    if snapshot.chat_scope == ResourceScope.ALL:
        chats = deps.ragflow_chat_service.list_all_chat_ids()
    else:
        chats = list(snapshot.chat_ids)

    return {
        "user": {"user_id": user.user_id, "username": user.username, "role": user.role, "group_id": user.group_id, "group_ids": user.group_ids},
        "snapshot": {
            "is_admin": snapshot.is_admin,
            "kb_scope": snapshot.kb_scope,
            "kb_refs": sorted(snapshot.kb_names),
            "chat_scope": snapshot.chat_scope,
            "chat_refs": sorted(snapshot.chat_ids),
            "permissions": snapshot.permissions_dict(),
        },
        "effective_access": {
            "accessible_kb_ids": sorted(set([x for x in kb_ids if isinstance(x, str) and x])),
            "accessible_kbs": sorted(set([x for x in kb_names if isinstance(x, str) and x])),
            "accessible_chats": sorted(set([x for x in chats if isinstance(x, str) and x])),
        },
    }


@router.get("/diagnostics/ragflow")
async def ragflow_diagnostics(ctx: AuthContextDep, _: AdminOnly):
    deps = ctx.deps
    ragflow = deps.ragflow_service
    chat = deps.ragflow_chat_service

    base_url = (getattr(ragflow, "config", {}) or {}).get("base_url")
    api_key = (getattr(ragflow, "config", {}) or {}).get("api_key") or ""

    datasets = []
    try:
        list_all = getattr(ragflow, "list_all_datasets", None)
        datasets = list_all() if callable(list_all) else ragflow.list_datasets()
    except Exception:
        datasets = []

    chats = []
    try:
        chats = chat.list_all_chat_ids()
    except Exception:
        chats = []

    return {
        "ragflow": {
            "config_path": str(getattr(ragflow, "config_path", "")),
            "base_url": base_url,
            "api_key_configured": (not is_placeholder_api_key(api_key)),
            "datasets_count": len(datasets or []),
            "datasets_sample": [
                {"id": ds.get("id"), "name": ds.get("name")}
                for ds in (datasets or [])[:20]
                if isinstance(ds, dict)
            ],
        },
        "chat": {
            "config_path": str(getattr(chat, "config_path", "")),
            "base_url": (getattr(chat, "config", {}) or {}).get("base_url"),
            "chat_refs_count": len(chats or []),
            "chat_refs_sample": (chats or [])[:20],
        },
    }
