from __future__ import annotations

from typing import Any

from .models import DataSecuritySettings


class DataSecuritySettingsPolicy:
    def has_standard_replica_mount(self) -> bool:
        return False

    def apply_runtime_overrides(self, stored: dict[str, Any]) -> dict[str, Any]:
        effective = dict(stored)
        effective["standard_replica_mount_active"] = False
        return effective

    def constrain_updates(self, fields: dict[str, Any]) -> dict[str, Any]:
        return dict(fields)

    def build_settings(self, stored: dict[str, Any]) -> DataSecuritySettings:
        return DataSecuritySettings(**self.apply_runtime_overrides(stored))
