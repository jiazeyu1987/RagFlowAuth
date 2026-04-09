import {
  buildGroupAssignmentModalState,
  buildToolAssignmentModalState,
} from './userManagementDerivedState';

export const buildClosedResetPasswordState = () => ({
  showResetPasswordModal: false,
  resetPasswordUser: null,
  resetPasswordValue: '',
  resetPasswordConfirm: '',
  resetPasswordError: null,
});

export const buildOpenedResetPasswordState = (targetUser) => ({
  showResetPasswordModal: true,
  resetPasswordUser: targetUser,
  resetPasswordValue: '',
  resetPasswordConfirm: '',
  resetPasswordError: null,
});

export const buildClosedDisableUserState = () => ({
  showDisableUserModal: false,
  disableTargetUser: null,
  disableMode: 'immediate',
  disableUntilDate: '',
  disableUserError: null,
});

export const buildOpenedDisableUserState = (targetUser) => ({
  showDisableUserModal: true,
  disableTargetUser: targetUser,
  disableMode: 'immediate',
  disableUntilDate: '',
  disableUserError: null,
});

export const buildClosedGroupAssignmentState = () => ({
  showGroupModal: false,
  editingGroupUser: null,
  selectedGroupIds: [],
});

export const buildOpenedGroupAssignmentState = ({ targetUser, availableGroups }) => ({
  showGroupModal: true,
  ...buildGroupAssignmentModalState({ targetUser, availableGroups }),
});

export const buildClosedToolAssignmentState = () => ({
  showToolModal: false,
  editingToolUser: null,
  selectedToolIds: [],
});

export const buildOpenedToolAssignmentState = ({ targetUser, availableToolIds }) => ({
  showToolModal: true,
  ...buildToolAssignmentModalState({ targetUser, availableToolIds }),
});
