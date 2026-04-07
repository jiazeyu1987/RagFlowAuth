from __future__ import annotations


def build_create_group_payload(data, *, created_by: str) -> dict:
    payload = data.model_dump()
    payload["created_by"] = created_by
    return payload


def build_update_group_payload(data) -> dict:
    payload = {key: value for key, value in data.model_dump().items() if value is not None}
    fields_set = set(getattr(data, "model_fields_set", set()) or set())
    if "folder_id" in fields_set and "folder_id" not in payload:
        payload["folder_id"] = None
    return payload


def merge_group_scope_payload(current_group: dict, payload: dict) -> dict:
    merged = dict(current_group or {})
    merged.update(payload or {})
    return merged
