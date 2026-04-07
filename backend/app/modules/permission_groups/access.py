from __future__ import annotations

from backend.app.modules.permission_groups.folder_access import (
    assert_folder_visible,
    build_group_folder_update_payload,
    get_visible_folder_scope,
    list_manageable_folder_snapshot,
    validate_folder_parent,
)
from backend.app.modules.permission_groups.management_access import (
    assert_group_management,
    chat_management_manager,
    get_manageable_group,
    get_manageable_knowledge_tree,
    knowledge_management_manager,
    list_assignable_groups,
    list_manageable_chat_resources,
    list_manageable_groups,
    list_manageable_knowledge_bases,
    validate_group_scope,
)
