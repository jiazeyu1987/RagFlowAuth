from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from backend.app.core.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    s = str(text or "")
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def _file_token_secret() -> str:
    return (
        str(getattr(settings, "ONLYOFFICE_FILE_TOKEN_SECRET", "") or "").strip()
        or str(getattr(settings, "JWT_SECRET_KEY", "") or "")
    )


def create_file_access_token(claims: dict[str, Any], ttl_seconds: int | None = None) -> str:
    secret = _file_token_secret()
    if not secret:
        raise RuntimeError("onlyoffice_file_token_secret_missing")

    ttl = int(ttl_seconds or settings.ONLYOFFICE_FILE_TOKEN_TTL_SECONDS or 300)
    now = int(time.time())
    payload = dict(claims or {})
    payload["iat"] = now
    payload["exp"] = now + max(30, ttl)

    body = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = _b64url_encode(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def parse_file_access_token(token: str) -> dict[str, Any]:
    secret = _file_token_secret()
    if not secret:
        raise RuntimeError("onlyoffice_file_token_secret_missing")

    value = str(token or "").strip()
    if "." not in value:
        raise ValueError("invalid_token_format")
    body, sig = value.split(".", 1)
    expected_sig = _b64url_encode(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("invalid_token_signature")

    payload = json.loads(_b64url_decode(body).decode("utf-8"))
    now = int(time.time())
    exp = int(payload.get("exp") or 0)
    if exp <= now:
        raise ValueError("token_expired")
    return payload
