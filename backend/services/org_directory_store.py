"""
Compatibility module.

The implementation is split into `backend/services/org_directory/`.
"""

from backend.services.org_directory import (
    Company,
    Department,
    Employee,
    OrgDirectoryAuditLog,
    OrgDirectoryStore,
    OrgStructureManager,
    OrgStructureRebuildSummary,
)

__all__ = [
    "Company",
    "Department",
    "Employee",
    "OrgDirectoryAuditLog",
    "OrgDirectoryStore",
    "OrgStructureManager",
    "OrgStructureRebuildSummary",
]
