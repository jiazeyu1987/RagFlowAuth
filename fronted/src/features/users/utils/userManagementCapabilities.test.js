import { buildUserManagementCapabilities } from './userManagementCapabilities';

describe('buildUserManagementCapabilities', () => {
  it('derives admin-only actions for admin actors', () => {
    expect(
      buildUserManagementCapabilities({
        role: 'admin',
        user_id: 'admin-1',
      })
    ).toEqual({
      actorRole: 'admin',
      actorUserId: 'admin-1',
      isAdminUser: true,
      isSubAdminUser: false,
      canCreateUsers: true,
      canEditUserPolicy: true,
      canResetPasswords: true,
      canToggleUserStatus: true,
      canDeleteUsers: true,
      canAssignGroups: false,
      canAssignTools: false,
    });
  });

  it('derives sub-admin assignment and password capabilities without admin-only actions', () => {
    expect(
      buildUserManagementCapabilities({
        role: 'sub_admin',
        user_id: 'sub-1',
      })
    ).toEqual({
      actorRole: 'sub_admin',
      actorUserId: 'sub-1',
      isAdminUser: false,
      isSubAdminUser: true,
      canCreateUsers: false,
      canEditUserPolicy: false,
      canResetPasswords: true,
      canToggleUserStatus: false,
      canDeleteUsers: false,
      canAssignGroups: true,
      canAssignTools: true,
    });
  });

  it('normalizes missing actor fields to empty strings', () => {
    expect(buildUserManagementCapabilities(null)).toEqual({
      actorRole: '',
      actorUserId: '',
      isAdminUser: false,
      isSubAdminUser: false,
      canCreateUsers: false,
      canEditUserPolicy: false,
      canResetPasswords: false,
      canToggleUserStatus: false,
      canDeleteUsers: false,
      canAssignGroups: false,
      canAssignTools: false,
    });
  });
});
