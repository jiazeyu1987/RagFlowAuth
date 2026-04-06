from __future__ import annotations

from pathlib import Path

from backend.database.tenant_paths import resolve_tenant_db_root
from backend.services.users.store import UserStore


def resolve_user_display_names(deps, user_ids: set[str] | list[str] | tuple[str, ...]) -> dict[str, str]:
    ids = {str(item).strip() for item in (user_ids or set()) if str(item or "").strip()}
    if not ids:
        return {}

    candidates: list[object] = []
    primary_store = getattr(deps, "user_store", None)
    if primary_store is not None:
        candidates.append(primary_store)

    db_path = getattr(primary_store, "db_path", None)
    if db_path:
        try:
            db_file = Path(str(db_path)).resolve()
            tenant_root = resolve_tenant_db_root(base_db_path=str(db_file))
            if tenant_root.resolve() in db_file.parents:
                candidates.append(UserStore(db_path=str(tenant_root.parent / "auth.db")))
        except Exception:
            pass

    result: dict[str, str] = {}
    seen_store_ids: set[int] = set()
    for store in candidates:
        if id(store) in seen_store_ids:
            continue
        seen_store_ids.add(id(store))
        try:
            mapping = store.get_display_names_by_ids(ids)
        except Exception:
            mapping = {}
        for key, value in (mapping or {}).items():
            normalized_key = str(key or "").strip()
            normalized_value = str(value or "").strip()
            if normalized_key and normalized_value and normalized_key not in result:
                result[normalized_key] = normalized_value
    return result
