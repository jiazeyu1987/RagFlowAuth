from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.signature_support import resolve_signature_service
from backend.models.auth import SignatureChallengeRequest, SignatureChallengeResponse
from backend.services.electronic_signature import ElectronicSignatureError


router = APIRouter()


@router.post("/electronic-signatures/challenge", response_model=SignatureChallengeResponse)
def signature_challenge(
    request_data: SignatureChallengeRequest,
    ctx: AuthContextDep,
):
    try:
        result = resolve_signature_service(ctx.deps).issue_challenge(
            user=ctx.user,
            password=request_data.password,
            user_store=ctx.deps.user_store,
        )
    except ElectronicSignatureError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc
    return SignatureChallengeResponse(
        sign_token=str(result["sign_token"]),
        expires_at_ms=int(result["expires_at_ms"]),
    )
