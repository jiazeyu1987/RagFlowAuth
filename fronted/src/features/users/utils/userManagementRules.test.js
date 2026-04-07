import {
  buildDisableUserPayload,
  buildEnableUserPayload,
  canAssignManagedUserGroups,
  canResetManagedUserPassword,
  formatDateForInput,
  getValidAssignableGroupIds,
  isUserLoginDisabled,
  mapRoleToUserType,
} from './userManagementRules';
import { DISABLE_UNTIL_REQUIRED_MESSAGE } from './userAccessPolicy';

describe('userManagementRules', () => {
  it('maps backend roles into the editable user type', () => {
    expect(mapRoleToUserType('sub_admin')).toBe('sub_admin');
    expect(mapRoleToUserType('viewer')).toBe('normal');
    expect(mapRoleToUserType('admin')).toBe('normal');
  });

  it('detects disabled users from status and future disable windows', () => {
    expect(isUserLoginDisabled({ status: 'inactive' }, 1000)).toBe(true);
    expect(
      isUserLoginDisabled(
        { status: 'active', disable_login_enabled: true, disable_login_until_ms: 2000 },
        1000
      )
    ).toBe(true);
    expect(
      isUserLoginDisabled(
        { status: 'active', disable_login_enabled: true, disable_login_until_ms: 500 },
        1000
      )
    ).toBe(false);
  });

  it('formats timestamps for date inputs', () => {
    expect(formatDateForInput(Date.UTC(2099, 11, 31))).toBe('2099-12-31');
    expect(formatDateForInput(null)).toBe('');
  });

  it('builds immediate and scheduled disable payloads', () => {
    expect(buildDisableUserPayload({ mode: 'immediate' })).toEqual({
      status: 'inactive',
      disable_login_enabled: false,
      disable_login_until_ms: null,
    });

    expect(
      buildDisableUserPayload({
        mode: 'until',
        untilDate: '2099-12-31',
        nowMs: 1,
      })
    ).toEqual(
      expect.objectContaining({
        status: 'active',
        disable_login_enabled: true,
        disable_login_until_ms: expect.any(Number),
      })
    );
  });

  it('fails fast when scheduled disable date is missing', () => {
    expect(() => buildDisableUserPayload({ mode: 'until', untilDate: '', nowMs: 1 })).toThrow(
      DISABLE_UNTIL_REQUIRED_MESSAGE
    );
  });

  it('builds the normalized enable payload', () => {
    expect(buildEnableUserPayload()).toEqual({
      status: 'active',
      disable_login_enabled: false,
      disable_login_until_ms: null,
    });
  });

  it('allows password reset for admins, self sub-admin, and owned viewers only', () => {
    expect(
      canResetManagedUserPassword({
        actorRole: 'admin',
        actorUserId: 'admin-1',
        targetUser: { user_id: 'u-1', role: 'viewer' },
      })
    ).toBe(true);

    expect(
      canResetManagedUserPassword({
        actorRole: 'sub_admin',
        actorUserId: 'sub-1',
        targetUser: { user_id: 'sub-1', role: 'sub_admin' },
      })
    ).toBe(true);

    expect(
      canResetManagedUserPassword({
        actorRole: 'sub_admin',
        actorUserId: 'sub-1',
        targetUser: { user_id: 'u-1', role: 'viewer', manager_user_id: 'sub-1' },
      })
    ).toBe(true);

    expect(
      canResetManagedUserPassword({
        actorRole: 'sub_admin',
        actorUserId: 'sub-1',
        targetUser: { user_id: 'u-2', role: 'viewer', manager_user_id: 'sub-2' },
      })
    ).toBe(false);
  });

  it('allows group assignment for admins and only owned viewers under a sub admin', () => {
    expect(
      canAssignManagedUserGroups({
        actorRole: 'admin',
        actorUserId: 'admin-1',
        targetUser: { user_id: 'u-1', role: 'viewer', manager_user_id: 'sub-1' },
      })
    ).toBe(true);

    expect(
      canAssignManagedUserGroups({
        actorRole: 'sub_admin',
        actorUserId: 'sub-1',
        targetUser: { user_id: 'u-1', role: 'viewer', manager_user_id: 'sub-1' },
      })
    ).toBe(true);

    expect(
      canAssignManagedUserGroups({
        actorRole: 'sub_admin',
        actorUserId: 'sub-1',
        targetUser: { user_id: 'sub-2', role: 'sub_admin', manager_user_id: 'sub-1' },
      })
    ).toBe(false);

    expect(
      canAssignManagedUserGroups({
        actorRole: 'viewer',
        actorUserId: 'u-3',
        targetUser: { user_id: 'u-1', role: 'viewer', manager_user_id: 'sub-1' },
      })
    ).toBe(false);
  });

  it('drops stale and duplicate group ids against assignable groups', () => {
    expect(
      getValidAssignableGroupIds({
        availableGroups: [{ group_id: 7 }, { group_id: 9 }],
        groupIds: [11, 9, 7, 9, '7'],
      })
    ).toEqual([9, 7]);
  });
});
