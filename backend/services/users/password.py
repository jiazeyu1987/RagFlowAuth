import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


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

