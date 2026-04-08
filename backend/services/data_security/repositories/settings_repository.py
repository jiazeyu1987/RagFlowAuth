from __future__ import annotations

import time
from typing import Any, Callable


class DataSecuritySettingsRepository:
    ALLOWED_UPDATE_FIELDS = {
        "enabled",
        "interval_minutes",
        "target_mode",
        "target_ip",
        "target_share_name",
        "target_subdir",
        "target_local_dir",
        "ragflow_compose_path",
        "ragflow_project_name",
        "ragflow_stop_services",
        "auth_db_path",
        "full_backup_enabled",
        "full_backup_include_images",
        "backup_retention_max",
        "incremental_schedule",
        "full_backup_schedule",
        "replica_enabled",
        "replica_target_path",
        "replica_subdir_format",
    }

    def __init__(self, conn_factory: Callable[[], object]) -> None:
        self._conn_factory = conn_factory

    def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> Any:
        conn = self._conn_factory()
        try:
            return conn.execute(query, params).fetchone()
        finally:
            conn.close()

    def get_settings_record(self) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM data_security_settings WHERE id = 1")
        if not row:
            raise RuntimeError("data_security_settings not initialized")

        def get_col(key: str, default: Any = None) -> Any:
            try:
                return row[key]
            except Exception:
                return default

        try:
            backup_retention_max = int(get_col("backup_retention_max", 30) or 30)
        except Exception:
            backup_retention_max = 30

        return {
            "enabled": bool(row["enabled"]),
            "interval_minutes": int(row["interval_minutes"] or 1440),
            "target_mode": str(row["target_mode"] or "share"),
            "target_ip": row["target_ip"],
            "target_share_name": row["target_share_name"],
            "target_subdir": row["target_subdir"],
            "target_local_dir": row["target_local_dir"],
            "ragflow_compose_path": row["ragflow_compose_path"],
            "ragflow_project_name": row["ragflow_project_name"],
            "ragflow_stop_services": bool(row["ragflow_stop_services"]),
            "auth_db_path": str(row["auth_db_path"] or "data/auth.db"),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
            "last_run_at_ms": int(row["last_run_at_ms"]) if row["last_run_at_ms"] is not None else None,
            "upload_after_backup": bool(get_col("upload_after_backup", 0)),
            "upload_host": get_col("upload_host"),
            "upload_username": get_col("upload_username"),
            "upload_target_path": get_col("upload_target_path"),
            "full_backup_enabled": bool(get_col("full_backup_enabled", 0)),
            "full_backup_include_images": bool(get_col("full_backup_include_images", 1)),
            "backup_retention_max": max(1, min(100, backup_retention_max)),
            "incremental_schedule": get_col("incremental_schedule"),
            "full_backup_schedule": get_col("full_backup_schedule"),
            "last_incremental_backup_time_ms": (
                int(get_col("last_incremental_backup_time_ms"))
                if get_col("last_incremental_backup_time_ms") is not None
                else None
            ),
            "last_full_backup_time_ms": (
                int(get_col("last_full_backup_time_ms")) if get_col("last_full_backup_time_ms") is not None else None
            ),
            "replica_enabled": bool(get_col("replica_enabled", 0)),
            "replica_target_path": get_col("replica_target_path"),
            "replica_subdir_format": get_col("replica_subdir_format") or "flat",
        }

    def prepare_updates(self, updates: dict[str, Any]) -> dict[str, Any]:
        fields = {key: updates.get(key) for key in self.ALLOWED_UPDATE_FIELDS if key in updates}
        if "backup_retention_max" in fields:
            try:
                value = int(fields["backup_retention_max"])
                fields["backup_retention_max"] = max(1, min(100, value))
            except Exception:
                fields.pop("backup_retention_max", None)
        return fields

    def update_settings(self, fields: dict[str, Any]) -> None:
        conn = self._conn_factory()
        try:
            sets = ", ".join([f"{key} = ?" for key in fields.keys()])
            values = list(fields.values())
            conn.execute(f"UPDATE data_security_settings SET {sets} WHERE id = 1", values)
            conn.commit()
        finally:
            conn.close()

    def touch_last_run(self, when_ms: int | None = None) -> None:
        now_ms = int(time.time() * 1000) if when_ms is None else int(when_ms)
        self._update_timestamp_field("last_run_at_ms", now_ms)

    def update_last_incremental_backup_time(self, when_ms: int | None = None) -> None:
        now_ms = int(time.time() * 1000) if when_ms is None else int(when_ms)
        self._update_timestamp_field("last_incremental_backup_time_ms", now_ms)

    def update_last_full_backup_time(self, when_ms: int | None = None) -> None:
        now_ms = int(time.time() * 1000) if when_ms is None else int(when_ms)
        self._update_timestamp_field("last_full_backup_time_ms", now_ms)

    def _update_timestamp_field(self, field_name: str, when_ms: int) -> None:
        conn = self._conn_factory()
        try:
            conn.execute(f"UPDATE data_security_settings SET {field_name} = ? WHERE id = 1", (int(when_ms),))
            conn.commit()
        finally:
            conn.close()
