import {
  buildClosedGroupAssignmentState,
  buildClosedDisableUserState,
  buildClosedResetPasswordState,
  buildOpenedGroupAssignmentState,
  buildOpenedDisableUserState,
  buildOpenedResetPasswordState,
} from './userManagementModalState';

describe('userManagementModalState', () => {
  it('builds the closed reset-password modal state', () => {
    expect(buildClosedResetPasswordState()).toEqual({
      showResetPasswordModal: false,
      resetPasswordUser: null,
      resetPasswordValue: '',
      resetPasswordConfirm: '',
      resetPasswordError: null,
    });
  });

  it('builds the opened reset-password modal state', () => {
    expect(buildOpenedResetPasswordState({ user_id: 'u-1' })).toEqual({
      showResetPasswordModal: true,
      resetPasswordUser: { user_id: 'u-1' },
      resetPasswordValue: '',
      resetPasswordConfirm: '',
      resetPasswordError: null,
    });
  });

  it('builds the closed disable-user modal state', () => {
    expect(buildClosedDisableUserState()).toEqual({
      showDisableUserModal: false,
      disableTargetUser: null,
      disableMode: 'immediate',
      disableUntilDate: '',
      disableUserError: null,
    });
  });

  it('builds the opened disable-user modal state', () => {
    expect(buildOpenedDisableUserState({ user_id: 'u-2' })).toEqual({
      showDisableUserModal: true,
      disableTargetUser: { user_id: 'u-2' },
      disableMode: 'immediate',
      disableUntilDate: '',
      disableUserError: null,
    });
  });

  it('builds opened and closed group-assignment modal state', () => {
    expect(buildClosedGroupAssignmentState()).toEqual({
      showGroupModal: false,
      editingGroupUser: null,
      selectedGroupIds: [],
    });

    expect(
      buildOpenedGroupAssignmentState({
        targetUser: {
          user_id: 'u-3',
          role: 'viewer',
          manager_user_id: 'sub-1',
          group_ids: [7, 9, 11],
        },
        availableGroups: [{ group_id: 7 }, { group_id: 9 }],
      })
    ).toEqual({
      showGroupModal: true,
      editingGroupUser: {
        user_id: 'u-3',
        role: 'viewer',
        manager_user_id: 'sub-1',
        group_ids: [7, 9, 11],
      },
      selectedGroupIds: [7, 9],
    });
  });
});
