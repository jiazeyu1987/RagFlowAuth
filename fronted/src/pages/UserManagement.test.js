import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UserManagement from './UserManagement';
import { useUserManagement } from '../features/users/hooks/useUserManagement';

jest.mock('../features/users/hooks/useUserManagement', () => ({
  useUserManagement: jest.fn(),
}));

jest.mock('../features/users/components/UserFiltersPanel', () => () => (
  <div data-testid="users-filters-panel" />
));

jest.mock('../features/users/components/DepartmentCards', () => () => (
  <div data-testid="users-department-cards" />
));

jest.mock('../features/users/components/UsersTable', () => () => <div data-testid="users-table" />);

jest.mock('../features/users/components/modals/ResetPasswordModal', () => () => null);
jest.mock('../features/users/components/modals/GroupModal', () => () => null);
jest.mock('../features/users/components/modals/DisableUserModal', () => () => null);

const createHookState = (overrides = {}) => ({
  loading: false,
  error: null,
  canManageUsers: true,
  canCreateUsers: true,
  canEditUserPolicy: true,
  canResetPasswords: true,
  canToggleUserStatus: true,
  canDeleteUsers: true,
  canAssignGroups: true,
  showCreateModal: false,
  newUser: {
    full_name: '',
    username: '',
    password: '',
    email: '',
    manager_user_id: '',
    role: 'viewer',
    managed_kb_root_node_id: '',
    company_id: '1',
    department_id: '11',
    group_ids: [],
    max_login_sessions: 3,
    idle_timeout_minutes: 120,
  },
  createUserError: null,
  filters: {
    q: '',
    company_id: '',
    department_id: '',
    status: '',
    group_id: '',
    created_from: '',
    created_to: '',
  },
  availableGroups: [],
  editingGroupUser: null,
  showGroupModal: false,
  selectedGroupIds: [],
  showResetPasswordModal: false,
  resetPasswordUser: null,
  resetPasswordValue: '',
  resetPasswordConfirm: '',
  resetPasswordSubmitting: false,
  resetPasswordError: null,
  showPolicyModal: false,
  policyUser: null,
  policySubmitting: false,
  policyError: null,
  policyForm: {
    full_name: 'Alice',
    email: 'alice@example.com',
    manager_user_id: '',
    company_id: '1',
    department_id: '11',
    role: 'viewer',
    managed_kb_root_node_id: '',
    group_ids: [],
    max_login_sessions: 3,
    idle_timeout_minutes: 120,
    can_change_password: true,
    disable_account: false,
    disable_mode: 'immediate',
    disable_until_date: '',
  },
  statusUpdatingUserId: '',
  showDisableUserModal: false,
  disableTargetUser: null,
  disableMode: 'immediate',
  disableUntilDate: '',
  disableUserError: null,
  companies: [
    { id: 1, name: 'Acme' },
    { id: 2, name: 'Other' },
  ],
  departments: [
    { id: 11, name: 'QA' },
    { id: 12, name: 'IT' },
  ],
  kbDirectoryNodes: [
    { id: 'node-root-a', name: 'A目录', parent_id: '', path: '/A目录' },
    { id: 'node-child-a1', name: 'A1目录', parent_id: 'node-root-a', path: '/A目录/A1目录' },
  ],
  kbDirectoryLoading: false,
  kbDirectoryError: null,
  filteredUsers: [],
  groupedUsers: {},
  managerOptions: [
    { value: 'mgr-1', label: '直属主管A', company_id: 1 },
    { value: 'mgr-2', label: '跨公司主管', company_id: 2 },
    { value: 'u-1', label: 'Alice', company_id: 1 },
  ],
  setFilters: jest.fn(),
  setPolicyForm: jest.fn(),
  setResetPasswordValue: jest.fn(),
  setResetPasswordConfirm: jest.fn(),
  handleOpenCreateModal: jest.fn(),
  handleCloseCreateModal: jest.fn(),
  setNewUserField: jest.fn(),
  toggleNewUserGroup: jest.fn(),
  handleCreateUser: jest.fn((event) => event?.preventDefault?.()),
  handleDeleteUser: jest.fn(),
  handleToggleUserStatus: jest.fn(),
  handleOpenResetPassword: jest.fn(),
  handleCloseResetPassword: jest.fn(),
  handleSubmitResetPassword: jest.fn(),
  handleOpenPolicyModal: jest.fn(),
  handleClosePolicyModal: jest.fn(),
  handleTogglePolicyGroup: jest.fn(),
  handleSavePolicy: jest.fn(),
  handleCloseDisableUserModal: jest.fn(),
  handleChangeDisableMode: jest.fn(),
  handleChangeDisableUntilDate: jest.fn(),
  handleConfirmDisableUser: jest.fn(),
  handleAssignGroup: jest.fn(),
  handleCloseGroupModal: jest.fn(),
  toggleSelectedGroup: jest.fn(),
  handleSaveGroup: jest.fn(),
  handleResetFilters: jest.fn(),
  ...overrides,
});

describe('UserManagement manager fields', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders create modal manager selector and updates manager_user_id', async () => {
    const user = userEvent.setup();
    const hookState = createHookState({
      showCreateModal: true,
    });
    useUserManagement.mockReturnValue(hookState);

    render(<UserManagement />);

    const managerSelect = await screen.findByTestId('users-create-manager');
    expect(within(managerSelect).getByRole('option', { name: '直属主管A' })).toBeInTheDocument();
    expect(within(managerSelect).queryByRole('option', { name: '跨公司主管' })).not.toBeInTheDocument();

    await user.selectOptions(managerSelect, 'mgr-1');

    expect(hookState.setNewUserField).toHaveBeenCalledWith('manager_user_id', 'mgr-1');
  });

  it('renders policy modal manager selector and updates manager_user_id', async () => {
    const user = userEvent.setup();
    const hookState = createHookState({
      showPolicyModal: true,
      policyUser: {
        user_id: 'u-1',
        username: 'alice',
        company_id: 1,
      },
    });
    useUserManagement.mockReturnValue(hookState);

    render(<UserManagement />);

    const managerSelect = await screen.findByTestId('users-policy-manager');
    expect(within(managerSelect).getByRole('option', { name: '直属主管A' })).toBeInTheDocument();
    expect(within(managerSelect).queryByRole('option', { name: 'Alice' })).not.toBeInTheDocument();
    expect(within(managerSelect).queryByRole('option', { name: '跨公司主管' })).not.toBeInTheDocument();

    await user.selectOptions(managerSelect, 'mgr-1');

    expect(hookState.setPolicyForm).toHaveBeenCalledWith(
      expect.objectContaining({
        manager_user_id: 'mgr-1',
      })
    );
  });

  it('shows knowledge root selector for sub admin creation and updates managed root', async () => {
    const user = userEvent.setup();
    const hookState = createHookState({
      showCreateModal: true,
      newUser: {
        ...createHookState().newUser,
        role: 'sub_admin',
      },
    });
    useUserManagement.mockReturnValue(hookState);

    render(<UserManagement />);

    expect(await screen.findByTestId('users-kb-root-selector')).toBeInTheDocument();
    await user.click(screen.getByTestId('users-kb-root-node-node-root-a'));

    expect(hookState.setNewUserField).toHaveBeenCalledWith('managed_kb_root_node_id', 'node-root-a');
  });

  it('shows knowledge root selector for sub admin editing and updates managed root', async () => {
    const user = userEvent.setup();
    const hookState = createHookState({
      showPolicyModal: true,
      policyUser: {
        user_id: 'u-1',
        username: 'alice',
        company_id: 1,
      },
      policyForm: {
        ...createHookState().policyForm,
        role: 'sub_admin',
      },
    });
    useUserManagement.mockReturnValue(hookState);

    render(<UserManagement />);

    expect(await screen.findByTestId('users-kb-root-selector')).toBeInTheDocument();
    await user.click(screen.getByTestId('users-kb-root-node-node-root-a'));

    expect(hookState.setPolicyForm).toHaveBeenCalledWith(
      expect.objectContaining({
        managed_kb_root_node_id: 'node-root-a',
      })
    );
  });
});
