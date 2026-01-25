"""
Compatibility module.

The original implementation lived in this file and grew large over time.
It is now split into smaller modules under `backend/services/users/`.
"""

from backend.services.users import User, UserStore, hash_password

__all__ = ["User", "UserStore", "hash_password"]

