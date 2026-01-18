from __future__ import annotations

import sys
from pathlib import Path

from backend.app.core.permission_resolver import ResourceScope, resolve_permissions
from backend.app.dependencies import create_dependencies


def main() -> None:
    deps = create_dependencies()

    print("=" * 80)
    print("Quick check: users / resolver / RAGFlow datasets")
    print("=" * 80)

    try:
        datasets = deps.ragflow_service.list_datasets() or []
        print(f"\n1) RAGFlow datasets: total={len(datasets)}")
        for ds in datasets[:10]:
            if isinstance(ds, dict):
                print(f"  - {ds.get('name')} (id={ds.get('id')})")
    except Exception as e:
        datasets = []
        print(f"\n1) RAGFlow datasets: error={e}")

    users = deps.user_store.list_users(limit=1000) or []
    print(f"\n2) Users: total={len(users)}")
    for user in users:
        snapshot = resolve_permissions(deps, user)
        group_ids = list(getattr(user, "group_ids", None) or [])

        if snapshot.kb_scope == ResourceScope.ALL:
            kb_preview = ["*"]
        else:
            kb_preview = sorted(snapshot.kb_names)

        print(
            f"  - {user.username} (role={user.role}, groups={group_ids}) "
            f"kb_scope={snapshot.kb_scope} kb_refs={kb_preview} "
            f"can_upload={snapshot.can_upload} can_review={snapshot.can_review} "
            f"can_download={snapshot.can_download} can_delete={snapshot.can_delete}"
        )


if __name__ == "__main__":
    main()
