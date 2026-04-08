from __future__ import annotations

import hashlib
import hmac
import secrets

from .password_legacy import (
    is_legacy_password_hash,
    verify_legacy_password,
)


PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000


def _pbkdf2_digest(password: str, *, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = _pbkdf2_digest(password, salt=salt, iterations=PASSWORD_HASH_ITERATIONS)
    return f"{PASSWORD_HASH_SCHEME}${PASSWORD_HASH_ITERATIONS}${salt}${digest}"

def verify_password(password: str, password_hash: str | None) -> tuple[bool, bool]:
    stored = str(password_hash or "").strip()
    if not stored:
        return False, False

    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == PASSWORD_HASH_SCHEME:
        _, raw_iterations, salt, expected = parts
        try:
            iterations = int(raw_iterations)
        except Exception:
            return False, False
        actual = _pbkdf2_digest(password, salt=salt, iterations=iterations)
        return hmac.compare_digest(actual, expected), False

    if verify_legacy_password(password, stored):
        return True, True
    return False, False


def validate_password_requirements(
    password: str,
    old_password: str | None = None,
) -> bool:
    """
    Validate password meets security requirements.

    Requirements:
    - Minimum 6 characters
    - Must contain both letters and numbers
    - Cannot be a common password

    Args:
        password: The new password to validate
        old_password: Optional old password to prevent reuse

    Returns:
        True if password meets all requirements, False otherwise
    """
    # Minimum length check
    if len(password) < 6:
        return False

    # Must contain both letters and numbers
    has_letters = any(c.isalpha() for c in password)
    has_numbers = any(c.isdigit() for c in password)

    if not (has_letters and has_numbers):
        return False

    # Common passwords list (case-insensitive)
    common_passwords = {
        "password",
        "123456",
        "abc123",
        "qwerty",
        "admin",
    }

    if password.lower() in common_passwords:
        return False

    # New password cannot match old password
    if old_password is not None and password == old_password:
        return False

    return True
