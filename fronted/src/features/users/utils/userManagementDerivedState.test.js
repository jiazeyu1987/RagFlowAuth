import {
  buildGroupAssignmentModalState,
  isManagedKbRootSelectionInvalid,
  resolveUserStatusToggleAction,
} from './userManagementDerivedState';

describe('userManagementDerivedState', () => {
  it('detects invalid managed KB roots only for sub-admin policy users', () => {
    expect(
      isManagedKbRootSelectionInvalid({
        policyUserType: 'sub_admin',
        managedKbRootNodeId: 'node-1',
        managedKbRootPath: '',
        kbDirectoryNodes: [{ id: 'node-2', parent_id: '', path: '/B' }],
        selectedManagedKbRootNodeId: 'node-1',
      })
    ).toBe(true);

    expect(
      isManagedKbRootSelectionInvalid({
        policyUserType: 'normal',
        managedKbRootNodeId: 'node-1',
        managedKbRootPath: '',
        kbDirectoryNodes: [],
        selectedManagedKbRootNodeId: 'node-1',
      })
    ).toBe(false);
  });

  it('builds group assignment modal state using assignable group filtering', () => {
    expect(
      buildGroupAssignmentModalState({
        targetUser: {
          user_id: 'u-1',
          permission_groups: [{ group_id: 7 }, { group_id: 11 }],
        },
        availableGroups: [{ group_id: 11 }, { group_id: 12 }],
      })
    ).toEqual({
      editingGroupUser: {
        user_id: 'u-1',
        permission_groups: [{ group_id: 7 }, { group_id: 11 }],
      },
      selectedGroupIds: [11],
    });
  });

  it('resolves user status toggle actions', () => {
    expect(resolveUserStatusToggleAction(null)).toEqual({ type: 'ignore' });
    expect(resolveUserStatusToggleAction({ user_id: '1', username: 'admin' })).toEqual({ type: 'ignore' });
    expect(
      resolveUserStatusToggleAction({
        user_id: '1',
        username: 'alice',
        status: 'active',
        disable_login_enabled: false,
      })
    ).toEqual({ type: 'disable' });
    expect(
      resolveUserStatusToggleAction({
        user_id: '1',
        username: 'alice',
        status: 'active',
        disable_login_enabled: true,
        disable_login_until_ms: 4102444799000,
      })
    ).toEqual({ type: 'enable' });
  });
});
