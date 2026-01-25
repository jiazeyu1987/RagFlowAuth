"""
Compatibility module.

The implementation is split into `backend/services/data_security/`.
"""

from backend.services.data_security.backup_service import DataSecurityBackupService, _run

__all__ = ["DataSecurityBackupService", "_run"]

