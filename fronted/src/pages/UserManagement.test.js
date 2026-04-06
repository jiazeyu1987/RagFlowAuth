import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UserManagement from './UserManagement';
import useUserManagementPage from '../features/users/useUserManagementPage';

jest.mock('../features/users/useUserManagementPage', () => jest.fn());

jest.mock('../features/users/components/UserFiltersPanel', () => () => <div data-testid="users-filters-panel" />);
jest.mock('../features/users/components/DepartmentCards', () => () => <div data-testid="users-department-cards" />);
jest.mock('../features/users/components/UsersTable', () => () => <div data-testid="users-table" />);
jest.mock('../features/users/components/modals/ResetPasswordModal', () => () => null);
jest.mock('../features/users/components/modals/GroupModal', () => () => null);
jest.mock('../features/users/components/modals/DisableUserModal', () => () => null);

const createHookState = (overrides = {}) => ({
  isMobile: false,
  loading: false,
  error: null,
  isSubAdminUser: false,
  canManageUsers: true,
  canCreateUsers: true,
  canEditUserPolicy: true,
  canResetPasswords: true,
  canToggleUserStatus: true,
  canDeleteUsers: true,
  canAssignGroups: false,
  showCreateModal: false,
  newUser: {
    full_name: '',
    username: '',
    password: '',
    user_type: 'normal',
    manager_user_id: '',
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
    assignment_status: '',
    created_from: '',
    created_to: '',
  },
  availableGroups: [{ group_id: 7, group_name: '默认权限组' }],
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
    company_id: '1',
    department_id: '11',
    user_type: 'normal',
    manager_user_id: 'sub-1',
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
    { id: 11, name: 'QA', path_name: 'Acme / QA', company_id: 1 },
    { id: 12, name: 'IT', path_name: 'Other / IT', company_id: 2 },
  ],
  orgDirectoryError: null,
  kbDirectoryNodes: [
    { id: 'node-root-a', name: 'A目录', parent_id: '', path: '/A目录' },
    { id: 'node-child-a1', name: 'A1目录', parent_id: 'node-root-a', path: '/A目录/A1目录' },
  ],
  kbDirectoryLoading: false,
  kbDirectoryError: null,
  kbDirectoryCreateError: null,
  kbDirectoryCreatingRoot: false,
  managedKbRootInvalid: false,
  filteredUsers: [],
  groupedUsers: {},
  subAdminOptions: [{ value: 'sub-1', label: '子管理员A', username: 'sub_admin_a', company_id: 1 }],
  policySubAdminOptions: [{ value: 'sub-1', label: '子管理员A', username: 'sub_admin_a', company_id: 1 }],
  setFilters: jest.fn(),
  handleChangePolicyForm: jest.fn(),
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
  handleCreateModalRootDirectory: jest.fn(),
  handlePolicyRootDirectory: jest.fn(),
  ...overrides,
});

describe('UserManagement simplified user ownership forms', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the users table in the left column and support panels in the right column', () => {
    useUserManagementPage.mockReturnValue(createHookState());

    render(<UserManagement />);

    const layout = screen.getByTestId('users-management-layout');
    const listColumn = screen.getByTestId('users-management-list-column');
    const sideColumn = screen.getByTestId('users-management-side-column');

    expect(layout).toHaveStyle({ display: 'flex', flexDirection: 'row' });
    expect(within(listColumn).getByTestId('users-table')).toBeInTheDocument();
    expect(within(sideColumn).getByTestId('users-filters-panel')).toBeInTheDocument();
    expect(within(sideColumn).getByTestId('users-department-cards')).toBeInTheDocument();
  });

  it('does not render a duplicate page heading inside the content area', () => {
    useUserManagementPage.mockReturnValue(createHookState());

    render(<UserManagement />);

    expect(screen.queryByRole('heading', { level: 2 })).not.toBeInTheDocument();
  });

  it('hides the department summary panel for sub admins', () => {
    useUserManagementPage.mockReturnValue(
      createHookState({
        isSubAdminUser: true,
        canCreateUsers: false,
      })
    );

    render(<UserManagement />);

    expect(screen.getByTestId('users-filters-panel')).toBeInTheDocument();
    expect(screen.queryByTestId('users-department-cards')).not.toBeInTheDocument();
  });

  it('renders normal user create modal with sub admin selector and no permission groups', async () => {
    useUserManagementPage.mockReturnValue(createHookState({ showCreateModal: true }));

    render(<UserManagement />);

    const typeSelect = await screen.findByTestId('users-create-user-type');
    expect(within(typeSelect).getByRole('option', { name: '普通用户' })).toBeInTheDocument();
    expect(within(typeSelect).getByRole('option', { name: '子管理员' })).toBeInTheDocument();
    expect(screen.getByTestId('users-create-department')).toBeInTheDocument();
    expect(screen.getByTestId('users-create-sub-admin')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '子管理员A' })).toBeInTheDocument();
    expect(screen.queryByTestId('users-create-group-7')).not.toBeInTheDocument();
    expect(screen.queryByTestId('users-kb-root-selector')).not.toBeInTheDocument();
  });

  it('shows username when sub admin label only has account name', async () => {
    useUserManagementPage.mockReturnValue(
      createHookState({
        showCreateModal: true,
        subAdminOptions: [{ value: 'sub-1', label: 'wangxin', username: 'wangxin', company_id: 1 }],
      })
    );

    render(<UserManagement />);

    expect(await screen.findByRole('option', { name: 'wangxin' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /6567f115-49f7-49a3-86cf-2282ae823975/ })).not.toBeInTheDocument();
  });

  it('renders sub admin create modal with directory selector and create-root handler', async () => {
    const user = userEvent.setup();
    const base = createHookState();
    const hookState = createHookState({
      showCreateModal: true,
      newUser: {
        ...base.newUser,
        user_type: 'sub_admin',
      },
    });
    useUserManagementPage.mockReturnValue(hookState);

    render(<UserManagement />);

    expect(await screen.findByTestId('users-kb-root-selector')).toBeInTheDocument();
    expect(screen.getByTestId('users-create-group-7')).toBeInTheDocument();
    expect(screen.queryByTestId('users-create-sub-admin')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('users-kb-root-node-node-root-a'));

    expect(hookState.setNewUserField).toHaveBeenCalledWith('managed_kb_root_node_id', 'node-root-a');
  });

  it('renders normal user edit modal with sub admin selector and no permission groups', () => {
    useUserManagementPage.mockReturnValue(
      createHookState({
        showPolicyModal: true,
        policyUser: {
          user_id: 'u-1',
          username: 'alice',
          role: 'viewer',
        },
      })
    );

    render(<UserManagement />);

    expect(screen.getByTestId('users-policy-user-type')).toBeInTheDocument();
    expect(screen.getByTestId('users-policy-department')).toBeInTheDocument();
    expect(screen.getByTestId('users-policy-sub-admin')).toBeInTheDocument();
    expect(screen.queryByTestId('users-policy-group-7')).not.toBeInTheDocument();
    expect(screen.queryByTestId('users-kb-root-selector')).not.toBeInTheDocument();
  });

  it('renders sub admin edit modal with invalid-root warning and directory selector', async () => {
    const user = userEvent.setup();
    const base = createHookState();
    const hookState = createHookState({
      showPolicyModal: true,
      managedKbRootInvalid: true,
      policyUser: {
        user_id: 'u-1',
        username: 'alice',
        role: 'sub_admin',
      },
      policyForm: {
        ...base.policyForm,
        user_type: 'sub_admin',
        manager_user_id: '',
      },
    });
    useUserManagementPage.mockReturnValue(hookState);

    render(<UserManagement />);

    expect(await screen.findByTestId('users-kb-root-selector')).toBeInTheDocument();
    expect(screen.getByTestId('users-policy-invalid-kb-root')).toBeInTheDocument();
    expect(screen.getByTestId('users-policy-group-7')).toBeInTheDocument();
    expect(screen.queryByTestId('users-policy-sub-admin')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('users-kb-root-node-node-root-a'));

    expect(hookState.handleChangePolicyForm).toHaveBeenCalledWith(
      expect.objectContaining({
        managed_kb_root_node_id: 'node-root-a',
      })
    );
  });

  it('passes create-root handlers into both user modals', () => {
    const hookState = createHookState({
      showCreateModal: true,
      showPolicyModal: true,
      policyUser: { user_id: 'u-1', username: 'alice', role: 'sub_admin' },
      policyForm: {
        ...createHookState().policyForm,
        user_type: 'sub_admin',
      },
    });
    useUserManagementPage.mockReturnValue(hookState);

    render(<UserManagement />);

    expect(screen.getByTestId('users-kb-root-selector')).toBeInTheDocument();
  });

  it('shows org directory error in create modal when departments are unavailable', () => {
    useUserManagementPage.mockReturnValue(
      createHookState({
        showCreateModal: true,
        departments: [],
        orgDirectoryError: '组织管理中没有可用部门，无法创建或编辑用户',
      })
    );

    render(<UserManagement />);

    expect(screen.getByTestId('users-create-org-error')).toHaveTextContent(
      '组织管理中没有可用部门，无法创建或编辑用户'
    );
  });
});
