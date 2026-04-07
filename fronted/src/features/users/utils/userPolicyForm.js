import { formatDateForInput, isUserLoginDisabled, mapRoleToUserType } from './userManagementRules';

export const getUserPermissionGroupIds = (user) => {
  if (Array.isArray(user?.group_ids)) {
    return [...user.group_ids];
  }
  if (Array.isArray(user?.permission_groups)) {
    return user.permission_groups.map((group) => group.group_id);
  }
  return [];
};

export const buildPolicyFormFromUser = (user, nowMs = Date.now()) => {
  const disableUntilMs = Number(user?.disable_login_until_ms || 0);
  const hasFutureUntil = Number.isFinite(disableUntilMs) && disableUntilMs > nowMs;

  return {
    full_name: String(user?.full_name || ''),
    company_id: user?.company_id != null ? String(user.company_id) : '',
    department_id: user?.department_id != null ? String(user.department_id) : '',
    manager_user_id: String(user?.manager_user_id || ''),
    user_type: mapRoleToUserType(user?.role),
    managed_kb_root_node_id: String(user?.managed_kb_root_node_id || ''),
    group_ids: getUserPermissionGroupIds(user),
    max_login_sessions: Number(user?.max_login_sessions || 3),
    idle_timeout_minutes: Number(user?.idle_timeout_minutes || 120),
    can_change_password: user?.can_change_password !== false,
    disable_account: isUserLoginDisabled(user, nowMs),
    disable_mode: hasFutureUntil ? 'until' : 'immediate',
    disable_until_date: hasFutureUntil ? formatDateForInput(disableUntilMs) : '',
  };
};
