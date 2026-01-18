from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import ResourceScope

router = APIRouter()


@router.get("/me/kbs")
async def get_my_kbs(ctx: AuthContextDep):
    """
    Compatibility endpoint for older frontend calls.

    Returns:
      {
        "kb_ids": [...],   # preferred: dataset ids
        "kb_names": [...], # for display only
      }
    """
    deps = ctx.deps
    snapshot = ctx.snapshot

    if snapshot.kb_scope == ResourceScope.ALL:
        datasets = (
            deps.ragflow_service.list_all_datasets()
            if hasattr(deps.ragflow_service, "list_all_datasets")
            else deps.ragflow_service.list_datasets()
        )
        kb_ids = [ds.get("id") for ds in (datasets or []) if isinstance(ds, dict) and ds.get("id")]
        kb_names = [ds.get("name") for ds in (datasets or []) if isinstance(ds, dict) and ds.get("name")]
        return {"kb_ids": sorted(set(kb_ids)), "kb_names": sorted(set(kb_names))}

    if snapshot.kb_scope == ResourceScope.NONE:
        return {"kb_ids": [], "kb_names": []}

    refs = set(snapshot.kb_names)
    kb_ids = (
        list(deps.ragflow_service.normalize_dataset_ids(refs))
        if hasattr(deps.ragflow_service, "normalize_dataset_ids")
        else []
    )
    if not kb_ids:
        kb_ids = sorted(refs)

    kb_names = (
        list(deps.ragflow_service.resolve_dataset_names(refs))
        if hasattr(deps.ragflow_service, "resolve_dataset_names")
        else sorted(refs)
    )

    return {"kb_ids": sorted(set([x for x in kb_ids if isinstance(x, str) and x])), "kb_names": sorted(set([x for x in kb_names if isinstance(x, str) and x]))}

