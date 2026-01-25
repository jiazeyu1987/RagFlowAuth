"""
Compatibility module.

The implementation is split into `backend/services/org_directory/`.
"""

from backend.services.org_directory import Company, Department, OrgDirectoryAuditLog, OrgDirectoryStore

__all__ = ["Company", "Department", "OrgDirectoryAuditLog", "OrgDirectoryStore"]

