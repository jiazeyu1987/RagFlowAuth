from __future__ import annotations

from typing import Annotated

from authx import TokenPayload
from fastapi import Depends, HTTPException, Request

from backend.core.security import auth
from backend.app.dependencies import AppDependencies


def get_deps(request: Request) -> AppDependencies:
    return request.app.state.deps


async def get_current_payload(request: Request) -> TokenPayload:
    """
    Resolve the current access-token payload.

    Accepts:
    - Authorization: Bearer <access_token> (frontend default)
    - access_token cookie (AuthX compatible)
    - token query param (AuthX compatible)

    Always returns 401 (not 422) when token is missing/invalid.
    """
    token: str | None = None
    try:
        token = await auth.get_access_token_from_request(request)
    except Exception:
        # Fall back to explicit header parsing.
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip() or None

    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")

    try:
        return auth.verify_token(token, verify_type=True)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")


AuthRequired = Annotated[TokenPayload, Depends(get_current_payload)]
