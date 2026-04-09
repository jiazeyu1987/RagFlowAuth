const normalizeUserField = (value) => String(value || '');

export const buildUserManagementCapabilities = (user) => {
  const actorRole = normalizeUserField(user?.role);
  const actorUserId = normalizeUserField(user?.user_id);
  const isAdminUser = actorRole === 'admin';
  const isSubAdminUser = actorRole === 'sub_admin';

  return {
    actorRole,
    actorUserId,
    isAdminUser,
    isSubAdminUser,
    canCreateUsers: isAdminUser,
    canEditUserPolicy: isAdminUser,
    canResetPasswords: isAdminUser || isSubAdminUser,
    canToggleUserStatus: isAdminUser,
    canDeleteUsers: isAdminUser,
    canAssignGroups: isSubAdminUser,
    canAssignTools: isSubAdminUser,
  };
};
