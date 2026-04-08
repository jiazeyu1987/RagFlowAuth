from __future__ import annotations

from typing import Iterable, Sequence, Set

from .group_compat import normalize_legacy_group_ids, primary_group_id
from .models import User


USER_READ_COLUMNS = """
user_id, username, password_hash, email, role, group_id, company_id, department_id, status,
manager_user_id,
max_login_sessions, idle_timeout_minutes, can_change_password,
disable_login_enabled, disable_login_until_ms,
electronic_signature_enabled,
created_at_ms, last_login_at_ms, created_by, full_name, managed_kb_root_node_id,
password_changed_at_ms, credential_fail_count, credential_fail_window_started_at_ms,
credential_locked_until_ms, employee_user_id
""".strip()


def _normalize_optional_identifier(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def build_user_from_row(
    row: Sequence[object],
    *,
    group_ids: Iterable[int] | None = None,
) -> User:
    normalized_group_ids = normalize_legacy_group_ids(group_ids=group_ids)
    user = User(
        user_id=row[0],
        username=row[1],
        password_hash=row[2],
        email=row[3],
        full_name=row[19],
        manager_user_id=row[9],
        employee_user_id=_normalize_optional_identifier(row[25]),
        role=row[4],
        group_id=row[5],
        company_id=row[6],
        department_id=row[7],
        status=row[8],
        max_login_sessions=int(row[10] or 3),
        idle_timeout_minutes=int(row[11] or 120),
        can_change_password=bool(row[12]) if row[12] is not None else True,
        disable_login_enabled=bool(row[13]) if row[13] is not None else False,
        disable_login_until_ms=int(row[14]) if row[14] is not None else None,
        electronic_signature_enabled=bool(row[15]) if row[15] is not None else True,
        created_at_ms=row[16],
        last_login_at_ms=row[17],
        created_by=row[18],
        managed_kb_root_node_id=row[20],
        password_changed_at_ms=(int(row[21]) if row[21] is not None else None),
        credential_fail_count=int(row[22] or 0),
        credential_fail_window_started_at_ms=(int(row[23]) if row[23] is not None else None),
        credential_locked_until_ms=(int(row[24]) if row[24] is not None else None),
    )
    user.group_ids = normalized_group_ids
    user.group_id = primary_group_id(normalized_group_ids)
    return user


def normalize_lookup_ids(user_ids: Set[str]) -> list[str]:
    return [value for value in (user_ids or set()) if isinstance(value, str) and value]


def build_username_reference_map(rows: Sequence[Sequence[object]]) -> dict[str, str]:
    result: dict[str, str] = {}

    for row in rows:
        if not row or len(row) < 2:
            continue

        user_id = str(row[0] or "")
        username = str(row[1] or "")
        if user_id:
            result[user_id] = username
        if username:
            result[username] = username

    return result


def build_display_name_reference_map(rows: Sequence[Sequence[object]]) -> dict[str, str]:
    result: dict[str, str] = {}

    for row in rows:
        if not row or len(row) < 3:
            continue

        user_id = str(row[0] or "")
        username = str(row[1] or "")
        full_name = str(row[2] or "").strip()
        display_name = full_name or username
        if not display_name:
            continue
        if user_id:
            result[user_id] = display_name
        if username:
            result[username] = display_name

    return result
