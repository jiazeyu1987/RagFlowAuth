from __future__ import annotations

from typing import Any

from .audit import emit_notification_audit
from .helpers import normalized_name, optional_int_attr, string_attr
from .store import NotificationStore


class NotificationRecipientDirectoryService:
    def __init__(
        self,
        *,
        store: NotificationStore,
        dingtalk_adapter: Any,
        audit_log_manager: Any | None = None,
    ):
        self._store = store
        self._dingtalk_adapter = dingtalk_adapter
        self._audit_log_manager = audit_log_manager

    def rebuild_dingtalk_recipient_map_from_org(
        self,
        *,
        channel_id: str,
        user_store: Any,
        org_directory_store: Any,
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        channel = self._store.get_channel(str(channel_id or "").strip())
        if not channel:
            raise ValueError("notification_channel_not_found")
        if str(channel.get("channel_type") or "").strip().lower() != "dingtalk":
            raise ValueError("notification_channel_not_dingtalk")

        config = channel.get("config") or {}
        if not isinstance(config, dict):
            raise ValueError("notification_channel_config_invalid")

        self.validate_dingtalk_channel_access(channel=channel)
        org_employees = self.list_org_employees_for_recipient_map_rebuild(org_directory_store)
        recipient_map: dict[str, str] = {}
        recipient_directory, invalid_org_users = self.build_dingtalk_recipient_directory(org_employees)
        if invalid_org_users:
            raise ValueError("notification_dingtalk_org_directory_invalid")
        user_binding_summary = self.sync_employee_user_ids_from_org(
            user_store=user_store,
            org_employees=org_employees,
        )

        updated_config = dict(config)
        updated_config["recipient_map"] = recipient_map
        updated_config["recipient_directory"] = recipient_directory
        updated_channel = self._store.upsert_channel(
            channel_id=str(channel["channel_id"]),
            channel_type=str(channel["channel_type"]),
            name=str(channel["name"]),
            enabled=bool(channel.get("enabled")),
            config=updated_config,
        )

        summary = {
            "channel_id": str(updated_channel["channel_id"]),
            "org_user_count": len(org_employees),
            "directory_entry_count": len(recipient_directory),
            "alias_entry_count": len(recipient_map),
            "invalid_org_user_count": len(invalid_org_users),
            "invalid_org_users": invalid_org_users,
        }
        emit_notification_audit(
            self._audit_log_manager,
            action="notification_channel_recipient_map_rebuild",
            event_type="update",
            resource_type="notification_channel",
            resource_id=str(updated_channel["channel_id"]),
            before=channel,
            after=updated_channel,
            meta={**summary, **user_binding_summary},
            audit=audit,
        )
        return summary

    def validate_dingtalk_channel_access(self, *, channel: dict[str, Any]) -> None:
        validate_channel = getattr(self._dingtalk_adapter, "validate_channel", None)
        if not callable(validate_channel):
            raise RuntimeError("notification_dingtalk_validation_unavailable")
        try:
            validate_channel(channel=channel)
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc

    @staticmethod
    def list_org_employees_for_recipient_map_rebuild(org_directory_store: Any) -> list[Any]:
        list_employees = getattr(org_directory_store, "list_employees", None)
        if not callable(list_employees):
            raise RuntimeError("notification_org_directory_unavailable")
        employees = list(list_employees() or [])
        employees.sort(
            key=lambda item: (
                string_attr(item, "employee_user_id"),
                string_attr(item, "name"),
                optional_int_attr(item, "company_id") or 0,
                optional_int_attr(item, "department_id") or 0,
            )
        )
        return employees

    @staticmethod
    def build_dingtalk_recipient_directory(org_employees: list[Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
        directory: dict[str, dict[str, Any]] = {}
        invalid_org_users: list[dict[str, str]] = []
        duplicate_user_ids: set[str] = set()

        for employee in org_employees:
            employee_user_id = string_attr(employee, "employee_user_id")
            full_name = string_attr(employee, "name")
            if not employee_user_id:
                invalid_org_users.append(
                    {"employee_user_id": "", "full_name": full_name, "reason": "employee_user_id_missing"}
                )
                continue
            if employee_user_id in directory:
                duplicate_user_ids.add(employee_user_id)
                continue
            directory[employee_user_id] = {
                "full_name": full_name,
                "company_id": optional_int_attr(employee, "company_id"),
                "department_id": optional_int_attr(employee, "department_id"),
            }

        if duplicate_user_ids:
            duplicate_items: list[dict[str, str]] = []
            seen_duplicates: set[tuple[str, str]] = set()
            for employee in org_employees:
                employee_user_id = string_attr(employee, "employee_user_id")
                if employee_user_id not in duplicate_user_ids:
                    continue
                full_name = string_attr(employee, "name")
                key = (employee_user_id, full_name)
                if key in seen_duplicates:
                    continue
                seen_duplicates.add(key)
                duplicate_items.append(
                    {
                        "employee_user_id": employee_user_id,
                        "full_name": full_name,
                        "reason": "employee_user_id_duplicate",
                    }
                )
                directory.pop(employee_user_id, None)
            invalid_org_users.extend(duplicate_items)

        invalid_org_users.sort(
            key=lambda item: (
                str(item.get("reason") or ""),
                str(item.get("full_name") or ""),
                str(item.get("employee_user_id") or ""),
            )
        )
        return directory, invalid_org_users

    @staticmethod
    def sync_employee_user_ids_from_org(
        *,
        user_store: Any,
        org_employees: list[Any],
    ) -> dict[str, int]:
        list_users = getattr(user_store, "list_users", None)
        sync_employee_user_ids = getattr(user_store, "sync_employee_user_ids", None)
        if not callable(list_users) or not callable(sync_employee_user_ids):
            raise RuntimeError("notification_user_store_unavailable")

        users = list(list_users(status="active", limit=1000000) or [])
        employees_by_name: dict[str, list[Any]] = {}
        for employee in org_employees:
            name = normalized_name(string_attr(employee, "name"))
            if not name:
                continue
            employees_by_name.setdefault(name, []).append(employee)

        assignments: dict[str, str | None] = {}
        matched_user_count = 0
        unmatched_user_count = 0
        for user in users:
            user_id = string_attr(user, "user_id")
            if not user_id:
                continue

            full_name = normalized_name(string_attr(user, "full_name"))
            employee_user_id: str | None = None
            if full_name:
                candidates = list(employees_by_name.get(full_name) or [])
                company_id = optional_int_attr(user, "company_id")
                if company_id is not None:
                    candidates = [item for item in candidates if optional_int_attr(item, "company_id") == company_id]
                if len(candidates) > 1:
                    department_id = optional_int_attr(user, "department_id")
                    if department_id is not None:
                        candidates = [
                            item for item in candidates if optional_int_attr(item, "department_id") == department_id
                        ]
                if len(candidates) == 1:
                    employee_user_id = string_attr(candidates[0], "employee_user_id") or None

            assignments[user_id] = employee_user_id
            if employee_user_id:
                matched_user_count += 1
            else:
                unmatched_user_count += 1

        sync_employee_user_ids(assignments)
        return {"matched_user_count": matched_user_count, "unmatched_user_count": unmatched_user_count}
