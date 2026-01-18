from __future__ import annotations

import sys
from pathlib import Path

from backend.app.core.permission_resolver import resolve_permissions
from backend.app.dependencies import create_dependencies


def main() -> None:
    deps = create_dependencies()

    print("=== Permission groups (stored) ===")
    for group in deps.permission_group_store.list_groups() or []:
        print(
            f"- {group.get('group_name')} (id={group.get('group_id')}, users={group.get('user_count')}) "
            f"kb={group.get('accessible_kbs') or []} chats={group.get('accessible_chats') or []} "
            f"can_upload={bool(group.get('can_upload'))} can_review={bool(group.get('can_review'))} "
            f"can_download={bool(group.get('can_download'))} can_delete={bool(group.get('can_delete'))}"
        )

    print("\n=== Users (effective resolver snapshot) ===")
    for user in deps.user_store.list_users(limit=1000) or []:
        snapshot = resolve_permissions(deps, user)
        group_ids = list(getattr(user, "group_ids", None) or [])

        print(
            f"- {user.username} (role={user.role}, user_id={user.user_id}, groups={group_ids}) "
            f"kb_scope={snapshot.kb_scope} kb_refs={sorted(snapshot.kb_names)} "
            f"chat_scope={snapshot.chat_scope} chat_refs={sorted(snapshot.chat_ids)} "
            f"perms={snapshot.permissions_dict()}"
        )

    print("\n=== RAGFlow datasets (connectivity check) ===")
    try:
        datasets = deps.ragflow_service.list_datasets() or []
        print(f"- total={len(datasets)}")
        for ds in datasets[:10]:
            if isinstance(ds, dict):
                print(f"  - {ds.get('name')} (id={ds.get('id')})")
    except Exception as e:
        print(f"- error: {e}")


if __name__ == "__main__":
    main()
