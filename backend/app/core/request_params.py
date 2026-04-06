from __future__ import annotations

from fastapi import HTTPException, Request


def require_non_empty_query_param(request: Request, *, name: str, detail: str) -> str:
    value = str(request.query_params.get(name) or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail=detail)
    return value
