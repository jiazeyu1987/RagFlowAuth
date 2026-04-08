from __future__ import annotations

import hashlib
import hmac


LEGACY_SHA256_HEX_LENGTH = 64


def is_legacy_password_hash(password_hash: str | None) -> bool:
    value = str(password_hash or "").strip().lower()
    return len(value) == LEGACY_SHA256_HEX_LENGTH and all(ch in "0123456789abcdef" for ch in value)


def verify_legacy_password(password: str, password_hash: str | None) -> bool:
    stored = str(password_hash or "").strip().lower()
    if not is_legacy_password_hash(stored):
        return False
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)
