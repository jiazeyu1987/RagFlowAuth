import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UserManagement from './UserManagement';
import useUserManagementPage from '../features/users/useUserManagementPage';

jest.mock('../features/users/useUserManagementPage', () => jest.fn());
jest.mock('../features/orgDirectory/api', () => ({
  orgDirectoryApi: {
    getTree: jest.fn(() => new Promise(() => {})),
  },
}));

jest.mock('../features/users/components/UserFiltersPanel', () => () => <div data-testid="users-filters-panel" />);
jest.mock('../features/users/components/DepartmentCards', () => () => <div data-testid="users-department-cards" />);
jest.mock('../features/users/components/UsersTable', () => () => <div data-testid="users-table" />);
jest.mock('../features/users/components/modals/ResetPasswordModal', () => () => null);
jest.mock('../features/users/components/modals/GroupModal', () => () => null);
jest.mock('../features/users/components/modals/ToolModal', () => () => null);
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
  canAssignTools: false,
  showCreateModal: false,
  allUsers: [],
  newUser: {
    full_name: '',
    username: '',
    employee_user_id: '',
    password: '',
    user_type: 'normal',
    manager_user_id: '',
    managed_kb_root_node_id: '',
    company_id: '1',
    department_id: '11',
    group_ids: [],
    tool_ids: [],
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
  availableGroups: [{ group_id: 7, group_name: 'Group-7' }],
  availableTools: [
    { group_id: 'paper_download', group_name: 'Paper Download' },
    { group_id: 'drug_admin', group_name: 'Drug Admin' },
  ],
  assignableTools: [{ group_id: 'paper_download', group_name: 'Paper Download' }],
  editingGroupUser: null,
  showGroupModal: false,
  selectedGroupIds: [],
  editingToolUser: null,
  showToolModal: false,
  selectedToolIds: [],
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
    tool_ids: [],
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
    { id: 'node-root-a', name: 'Root A', parent_id: '', path: '/Root A' },
    { id: 'node-child-a1', name: 'Child A1', parent_id: 'node-root-a', path: '/Root A/Child A1' },
  ],
  kbDirectoryLoading: false,
  kbDirectoryError: null,
  kbDirectoryCreateError: null,
  kbDirectoryCreatingRoot: false,
  managedKbRootInvalid: false,
  filteredUsers: [],
  groupedUsers: {},
  subAdminOptions: [{ value: 'sub-1', label: 'Sub Admin A', username: 'sub_admin_a', company_id: 1 }],
  policySubAdminOptions: [{ value: 'sub-1', label: 'Sub Admin A', username: 'sub_admin_a', company_id: 1 }],
  setFilters: jest.fn(),
  handleChangePolicyForm: jest.fn(),
  setResetPasswordValue: jest.fn(),
  setResetPasswordConfirm: jest.fn(),
  handleOpenCreateModal: jest.fn(),
  handleCloseCreateModal: jest.fn(),
  setNewUserField: jest.fn(),
  toggleNewUserGroup: jest.fn(),
  toggleNewUserTool: jest.fn(),
  handleCreateUser: jest.fn((event) => event?.preventDefault?.()),
  handleDeleteUser: jest.fn(),
  handleToggleUserStatus: jest.fn(),
  handleOpenResetPassword: jest.fn(),
  handleCloseResetPassword: jest.fn(),
  handleSubmitResetPassword: jest.fn(),
  handleOpenPolicyModal: jest.fn(),
  handleClosePolicyModal: jest.fn(),
  handleTogglePolicyGroup: jest.fn(),
  handleTogglePolicyTool: jest.fn(),
  handleSavePolicy: jest.fn(),
  handleCloseDisableUserModal: jest.fn(),
  handleChangeDisableMode: jest.fn(),
  handleChangeDisableUntilDate: jest.fn(),
  handleConfirmDisableUser: jest.fn(),
  handleAssignGroup: jest.fn(),
  handleAssignTool: jest.fn(),
  handleCloseGroupModal: jest.fn(),
  toggleSelectedGroup: jest.fn(),
  handleSaveGroup: jest.fn(),
  handleCloseToolModal: jest.fn(),
  toggleSelectedTool: jest.fn(),
  handleSaveTool: jest.fn(),
  handleResetFilters: jest.fn(),
  handleCreateModalRootDirectory: jest.fn(),
  handlePolicyRootDirectory: jest.fn(),
  ...overrides,
});

describe('UserManagement page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the users table and side panels', () => {
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

  it('renders loading and error states', () => {
    useUserManagementPage.mockReturnValue(createHookState({ loading: true }));
    const { rerender } = render(<UserManagement />);
    expect(screen.getByText(/\u52a0\u8f7d/)).toBeInTheDocument();

    useUserManagementPage.mockReturnValue(createHookState({ error: 'network_error' }));
    rerender(<UserManagement />);
    expect(screen.getByText('错误: network_error')).toBeInTheDocument();
  });

  it('hides department summary panel for sub-admin actor', () => {
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

  it('renders normal-user create modal without tool checklist', async () => {
    useUserManagementPage.mockReturnValue(createHookState({ showCreateModal: true }));
    render(<UserManagement />);

    expect(await screen.findByTestId('users-create-user-type')).toBeInTheDocument();
    expect(screen.getByTestId('users-create-sub-admin')).toBeInTheDocument();
    expect(screen.queryByTestId('users-create-tool-paper_download')).not.toBeInTheDocument();
    expect(screen.queryByTestId('users-kb-root-selector')).not.toBeInTheDocument();
  });

  it('renders sub-admin create modal with tool checklist and managed-root selector', async () => {
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

    expect(await screen.findByTestId('users-create-tool-paper_download')).toBeInTheDocument();
    expect(screen.getByTestId('users-kb-root-selector')).toBeInTheDocument();
    expect(screen.queryByTestId('users-create-sub-admin')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('users-create-tool-paper_download'));
    expect(hookState.toggleNewUserTool).toHaveBeenCalledWith('paper_download', true);
  });

  it('renders normal-user policy modal without tool checklist', () => {
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
    expect(screen.getByTestId('users-policy-sub-admin')).toBeInTheDocument();
    expect(screen.queryByTestId('users-policy-tool-paper_download')).not.toBeInTheDocument();
    expect(screen.queryByTestId('users-kb-root-selector')).not.toBeInTheDocument();
  });

  it('renders sub-admin policy modal with tool checklist and invalid-root warning', async () => {
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
        tool_ids: ['paper_download'],
      },
    });
    useUserManagementPage.mockReturnValue(hookState);

    render(<UserManagement />);

    expect(await screen.findByTestId('users-policy-tool-paper_download')).toBeInTheDocument();
    expect(screen.getByTestId('users-policy-invalid-kb-root')).toBeInTheDocument();
    expect(screen.getByTestId('users-kb-root-selector')).toBeInTheDocument();
    expect(screen.queryByTestId('users-policy-sub-admin')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('users-policy-tool-paper_download'));
    expect(hookState.handleTogglePolicyTool).toHaveBeenCalledWith('paper_download', false);
  });

  it('shows org directory error in create modal', () => {
    useUserManagementPage.mockReturnValue(
      createHookState({
        showCreateModal: true,
        departments: [],
        orgDirectoryError: 'org_directory_missing_department',
      })
    );

    render(<UserManagement />);
    expect(screen.getByTestId('users-create-org-error')).toHaveTextContent('org_directory_missing_department');
  });

  it('passes create-root sections into both modals', () => {
    const hookState = createHookState({
      showCreateModal: true,
      newUser: {
        ...createHookState().newUser,
        user_type: 'sub_admin',
      },
      showPolicyModal: true,
      policyUser: { user_id: 'u-1', username: 'alice', role: 'sub_admin' },
      policyForm: {
        ...createHookState().policyForm,
        user_type: 'sub_admin',
      },
    });
    useUserManagementPage.mockReturnValue(hookState);

    render(<UserManagement />);
    expect(screen.getAllByTestId('users-kb-root-selector').length).toBeGreaterThanOrEqual(1);
  });
});
