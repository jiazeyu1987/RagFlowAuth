import { buildUserManagementState } from './userManagementState';

describe('userManagementState', () => {
  it('assembles the public hook state from feature slices', () => {
    const passwordReset = {
      showResetPasswordModal: true,
      handleOpenResetPassword: jest.fn(),
    };
    const groupAssignment = {
      showGroupModal: true,
      handleAssignGroup: jest.fn(),
    };
    const statusManagement = {
      showDisableUserModal: true,
      handleToggleUserStatus: jest.fn(),
    };

    const state = buildUserManagementState({
      capabilities: {
        isSubAdminUser: true,
        canCreateUsers: false,
        canEditUserPolicy: true,
        canResetPasswords: true,
        canToggleUserStatus: true,
        canDeleteUsers: false,
        canAssignGroups: true,
      },
      dataState: {
        allUsers: [{ user_id: 'u-1' }],
        loading: false,
        error: 'error',
        canManageUsers: true,
        availableGroups: [{ group_id: 7 }],
        companies: [{ id: 1 }],
        departments: [{ id: 11 }],
        orgDirectoryError: 'org error',
      },
      createManagement: {
        showCreateModal: true,
        newUser: { username: 'alice' },
        createUserError: 'create error',
        toggleNewUserGroup: jest.fn(),
      },
      policyManagement: {
        showPolicyModal: true,
        policyUser: { user_id: 'u-1' },
        policyError: 'policy error',
        policyForm: { user_type: 'normal' },
        handleTogglePolicyGroup: jest.fn(),
      },
      knowledgeDirectoryState: {
        kbDirectoryNodes: [{ id: 'node-1' }],
        kbDirectoryDisabledNodeIds: ['node-2'],
        kbDirectoryLoading: true,
        kbDirectoryError: 'kb error',
        kbDirectoryCreateError: 'kb create error',
        kbDirectoryCreatingRoot: true,
        managedKbRootInvalid: true,
        handleCreateModalRootDirectory: jest.fn(),
        handlePolicyRootDirectory: jest.fn(),
      },
      viewModel: {
        filters: { q: 'alice' },
        filteredUsers: [{ user_id: 'u-1' }],
        groupedUsers: { QA: [] },
        subAdminOptions: [{ value: 'sub-1' }],
        policySubAdminOptions: [{ value: 'sub-2' }],
        setFilters: jest.fn(),
        handleResetFilters: jest.fn(),
      },
      actions: {
        policySubmitting: true,
        handleOpenCreateModal: jest.fn(),
        handleCloseCreateModal: jest.fn(),
        setNewUserField: jest.fn(),
        handleCreateUser: jest.fn(),
        handleOpenPolicyModal: jest.fn(),
        handleClosePolicyModal: jest.fn(),
        handleChangePolicyForm: jest.fn(),
        handleSavePolicy: jest.fn(),
      },
      passwordReset,
      groupAssignment,
      statusManagement,
      deletion: {
        handleDeleteUser: jest.fn(),
      },
    });

    expect(state).toEqual(
      expect.objectContaining({
        allUsers: [{ user_id: 'u-1' }],
        loading: false,
        error: 'error',
        isSubAdminUser: true,
        canManageUsers: true,
        canCreateUsers: false,
        canAssignGroups: true,
        showCreateModal: true,
        newUser: { username: 'alice' },
        createUserError: 'create error',
        showPolicyModal: true,
        policyUser: { user_id: 'u-1' },
        policySubmitting: true,
        policyError: 'policy error',
        companies: [{ id: 1 }],
        departments: [{ id: 11 }],
        kbDirectoryNodes: [{ id: 'node-1' }],
        kbDirectoryDisabledNodeIds: ['node-2'],
        filteredUsers: [{ user_id: 'u-1' }],
        subAdminOptions: [{ value: 'sub-1' }],
        policySubAdminOptions: [{ value: 'sub-2' }],
        showResetPasswordModal: true,
        showGroupModal: true,
        showDisableUserModal: true,
      })
    );
    expect(state.handleOpenResetPassword).toBe(passwordReset.handleOpenResetPassword);
    expect(state.handleAssignGroup).toBe(groupAssignment.handleAssignGroup);
    expect(state.handleToggleUserStatus).toBe(statusManagement.handleToggleUserStatus);
  });
});
