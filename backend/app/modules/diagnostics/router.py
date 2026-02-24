from __future__ import annotations

from fastapi import APIRouter
from fastapi import Request
import sys
from pathlib import Path

from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.core.permission_resolver import ResourceScope
from backend.services.ragflow_config import is_placeholder_api_key


router = APIRouter()


@router.get("/diagnostics/routes")
async def routes_diagnostics(request: Request, _: AdminOnly):
    """
    Quick runtime verification for route wiring.

    Motivation: when users run `python -m backend`, they may have multiple envs/processes.
    If a UI action returns 405, this endpoint makes it obvious which methods are actually
    registered on the running server (without reading code).
    """

    targets = [
        "/api/datasets",
        "/api/chats",
        "/api/search",
    ]

    by_path: dict[str, list[str]] = {}
    for r in getattr(request.app, "routes", []) or []:
        path = getattr(r, "path", None)
        if path not in targets:
            continue
        methods = getattr(r, "methods", None) or set()
        by_path[path] = sorted([m for m in methods if isinstance(m, str)])

    # Keep output stable even if a route is missing.
    for p in targets:
        by_path.setdefault(p, [])

    return {"routes": by_path}


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


@router.get("/diagnostics/build")
async def build_diagnostics(_: AdminOnly):
    """
    Runtime build/code fingerprint.

    Motivation: This project is often run via multiple Python envs/processes (Windows).
    When behavior looks "stale", this endpoint helps verify which interpreter + files
    the server is actually running.
    """

    def stat_of(p: Path) -> dict:
        try:
            st = p.stat()
            return {
                "path": str(p),
                "exists": True,
                "mtime_ns": getattr(st, "st_mtime_ns", None) or int(st.st_mtime * 1_000_000_000),
                "size": int(st.st_size),
            }
        except Exception:
            return {"path": str(p), "exists": False}

    try:
        import backend.services.ragflow_chat_service as rcs

        ragflow_chat_service_path = Path(getattr(rcs, "__file__", "") or "")
    except Exception:
        ragflow_chat_service_path = Path("")

    try:
        import backend.app.modules.chat.router as chat_router

        chat_router_path = Path(getattr(chat_router, "__file__", "") or "")
    except Exception:
        chat_router_path = Path("")

    return {
        "python": {"executable": sys.executable, "version": sys.version},
        "files": {
            "ragflow_chat_service": stat_of(ragflow_chat_service_path) if ragflow_chat_service_path else {"path": ""},
            "chat_router": stat_of(chat_router_path) if chat_router_path else {"path": ""},
        },
    }
