from __future__ import annotations

from backend.app.modules.users.group_assignment_access import (
    assert_sub_admin_group_assignment_only,
    normalize_requested_group_ids,
    validate_permission_group_tool_scope,
    validate_sub_admin_assignable_group_ids,
)
from backend.app.modules.users.management_access import (
    assert_can_reset_password,
    assert_manageable_target_user,
    assert_sub_admin_can_manage_users,
    assert_sub_admin_owned_viewer,
    chat_management_manager,
    get_manageable_target_user,
    MANAGEABLE_USER_DETAIL,
    knowledge_management_manager,
    resolve_password_reset_target,
    resolve_sub_admin_company_id,
    resolve_user_list_scope,
)
