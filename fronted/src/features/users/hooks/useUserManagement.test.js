import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useUserManagement } from './useUserManagement';
import { useAuth } from '../../../hooks/useAuth';
import { usersApi } from '../api';
import { permissionGroupsApi } from '../../permissionGroups/api';
import { orgDirectoryApi } from '../../orgDirectory/api';
import { knowledgeApi } from '../../knowledge/api';

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../api', () => ({
  usersApi: {
    list: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    remove: jest.fn(),
    resetPassword: jest.fn(),
  },
}));

jest.mock('../../permissionGroups/api', () => ({
  permissionGroupsApi: {
    listAssignable: jest.fn(),
  },
}));

jest.mock('../../orgDirectory/api', () => ({
  orgDirectoryApi: {
    listCompanies: jest.fn(),
    listDepartments: jest.fn(),
  },
}));

jest.mock('../../knowledge/api', () => ({
  knowledgeApi: {
    listKnowledgeDirectories: jest.fn(),
    createKnowledgeDirectory: jest.fn(),
  },
}));

function HookHarness() {
  const hook = useUserManagement();
  return (
    <div>
      <button type="button" data-testid="open-create" onClick={hook.handleOpenCreateModal}>
        open-create
      </button>
      <button type="button" data-testid="set-type-sub-admin" onClick={() => hook.setNewUserField('user_type', 'sub_admin')}>
        set-type-sub-admin
      </button>
      <button type="button" data-testid="set-company" onClick={() => hook.setNewUserField('company_id', '1')}>
        set-company
      </button>
      <button type="button" data-testid="set-company-2" onClick={() => hook.setNewUserField('company_id', '2')}>
        set-company-2
      </button>
      <button type="button" data-testid="set-department" onClick={() => hook.setNewUserField('department_id', '11')}>
        set-department
      </button>
      <button type="button" data-testid="set-create-root-node" onClick={() => hook.setNewUserField('managed_kb_root_node_id', 'node-1')}>
        set-create-root-node
      </button>
      <button type="button" data-testid="set-manager" onClick={() => hook.setNewUserField('manager_user_id', 'sub-1')}>
        set-manager
      </button>
      <button type="button" data-testid="select-create-group-7" onClick={() => hook.toggleNewUserGroup(7, true)}>
        select-create-group-7
      </button>
      <button type="button" data-testid="submit-create" onClick={() => hook.handleCreateUser({ preventDefault() {} })}>
        submit-create
      </button>
      <button type="button" data-testid="create-root-create" onClick={() => hook.handleCreateModalRootDirectory('New Root')}>
        create-root-create
      </button>
      <button
        type="button"
        data-testid="open-policy-normal"
        onClick={() =>
          hook.handleOpenPolicyModal({
            user_id: 'u-1',
            username: 'alice',
            role: 'viewer',
            full_name: 'Alice',
            company_id: 1,
            department_id: 11,
            manager_user_id: 'sub-1',
            group_ids: [7],
            managed_kb_root_node_id: '',
            max_login_sessions: 3,
            idle_timeout_minutes: 120,
            can_change_password: true,
            status: 'active',
          })
        }
      >
        open-policy-normal
      </button>
      <button
        type="button"
        data-testid="open-policy-sub-admin"
        onClick={() =>
          hook.handleOpenPolicyModal({
            user_id: 'u-2',
            username: 'suba',
            role: 'sub_admin',
            full_name: 'Sub A',
            company_id: 1,
            department_id: 11,
            group_ids: [7],
            managed_kb_root_node_id: 'node-1',
            managed_kb_root_path: null,
            max_login_sessions: 3,
            idle_timeout_minutes: 120,
            can_change_password: true,
            status: 'active',
          })
        }
      >
        open-policy-sub-admin
      </button>
      <button
        type="button"
        data-testid="policy-set-normal"
        onClick={() =>
          hook.handleChangePolicyForm((prev) => ({
            ...prev,
            user_type: 'normal',
            manager_user_id: 'sub-1',
            managed_kb_root_node_id: 'node-1',
          }))
        }
      >
        policy-set-normal
      </button>
      <button
        type="button"
        data-testid="policy-set-normal-empty-manager"
        onClick={() =>
          hook.handleChangePolicyForm((prev) => ({
            ...prev,
            user_type: 'normal',
            manager_user_id: '',
          }))
        }
      >
        policy-set-normal-empty-manager
      </button>
      <button type="button" data-testid="submit-policy" onClick={hook.handleSavePolicy}>
        submit-policy
      </button>
      <button type="button" data-testid="select-policy-group-7" onClick={() => hook.handleTogglePolicyGroup(7, true)}>
        select-policy-group-7
      </button>
      <button
        type="button"
        data-testid="assign-owned-user"
        onClick={() =>
          hook.handleAssignGroup({ user_id: 'u-owned', role: 'viewer', manager_user_id: 'sub-actor', group_ids: [7] })
        }
      >
        assign-owned-user
      </button>
      <button
        type="button"
        data-testid="assign-other-user"
        onClick={() =>
          hook.handleAssignGroup({ user_id: 'u-other', role: 'viewer', manager_user_id: 'someone-else', group_ids: [7] })
        }
      >
        assign-other-user
      </button>
      <button
        type="button"
        data-testid="assign-owned-user-stale-groups"
        onClick={() =>
          hook.handleAssignGroup({ user_id: 'u-owned-stale', role: 'viewer', manager_user_id: 'sub-actor', group_ids: [11, 7] })
        }
      >
        assign-owned-user-stale-groups
      </button>
      <button type="button" data-testid="save-group" onClick={hook.handleSaveGroup}>
        save-group
      </button>
      <button
        type="button"
        data-testid="open-reset-self"
        onClick={() =>
          hook.handleOpenResetPassword({ user_id: 'sub-actor', role: 'sub_admin', username: 'sub_admin_a' })
        }
      >
        open-reset-self
      </button>
      <button
        type="button"
        data-testid="open-reset-owned"
        onClick={() =>
          hook.handleOpenResetPassword({ user_id: 'u-owned', role: 'viewer', manager_user_id: 'sub-actor', username: 'viewer_a' })
        }
      >
        open-reset-owned
      </button>
      <button
        type="button"
        data-testid="open-reset-other-viewer"
        onClick={() =>
          hook.handleOpenResetPassword({ user_id: 'u-other', role: 'viewer', manager_user_id: 'someone-else', username: 'viewer_b' })
        }
      >
        open-reset-other-viewer
      </button>
      <button
        type="button"
        data-testid="open-reset-other-sub-admin"
        onClick={() =>
          hook.handleOpenResetPassword({ user_id: 'sub-other', role: 'sub_admin', username: 'sub_admin_b' })
        }
      >
        open-reset-other-sub-admin
      </button>
      <button type="button" data-testid="close-reset" onClick={hook.handleCloseResetPassword}>
        close-reset
      </button>
      <div data-testid="create-error">{hook.createUserError || ''}</div>
      <div data-testid="policy-error">{hook.policyError || ''}</div>
      <div data-testid="org-error">{hook.orgDirectoryError || ''}</div>
      <div data-testid="kb-root-invalid">{hook.managedKbRootInvalid ? 'yes' : 'no'}</div>
      <div data-testid="assign-groups-flag">{hook.canAssignGroups ? 'yes' : 'no'}</div>
      <div data-testid="selected-group-ids">{hook.selectedGroupIds.join(',')}</div>
      <div data-testid="reset-passwords-flag">{hook.canResetPasswords ? 'yes' : 'no'}</div>
      <div data-testid="show-group-modal">{hook.showGroupModal ? 'yes' : 'no'}</div>
      <div data-testid="show-reset-password-modal">{hook.showResetPasswordModal ? 'yes' : 'no'}</div>
    </div>
  );
}

describe('useUserManagement user type payloads', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: { role: 'admin', user_id: 'admin-1' },
      can: jest.fn(() => true),
    });
    usersApi.list.mockResolvedValue([
      { user_id: 'sub-1', username: 'sub_admin_a', full_name: '子管理员A', role: 'sub_admin', status: 'active', company_id: 1 },
      { user_id: 'viewer-1', username: 'viewer_a', full_name: '普通用户B', role: 'viewer', status: 'active', company_id: 1, manager_user_id: 'sub-1' },
    ]);
    usersApi.create.mockResolvedValue({});
    usersApi.update.mockResolvedValue({});
    permissionGroupsApi.listAssignable.mockResolvedValue({ ok: true, data: [{ group_id: 7, group_name: 'G7' }] });
    orgDirectoryApi.listCompanies.mockResolvedValue([{ id: 1, name: 'Acme' }, { id: 2, name: 'Beta' }]);
    orgDirectoryApi.listDepartments.mockResolvedValue([
      { id: 11, name: 'QA', company_id: 1 },
      { id: 21, name: 'Ops', company_id: 2 },
    ]);
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [{ id: 'node-1', name: '目录A', parent_id: '', path: '/目录A' }],
      datasets: [],
    });
    knowledgeApi.createKnowledgeDirectory.mockResolvedValue({ node: { id: 'node-created' } });
  });

  it('requires manager user when creating normal user', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-company'));
    await user.click(screen.getByTestId('set-department'));
    await user.click(screen.getByTestId('submit-create'));

    await waitFor(() => {
      expect(screen.getByTestId('create-error')).toHaveTextContent('请选择归属子管理员');
    });
    expect(usersApi.create).not.toHaveBeenCalled();
  });

  it('normal user create payload includes manager user and clears permission groups', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-company'));
    await user.click(screen.getByTestId('set-department'));
    await user.click(screen.getByTestId('set-manager'));
    await user.click(screen.getByTestId('submit-create'));

    await waitFor(() => expect(usersApi.create).toHaveBeenCalled());
    expect(usersApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        role: 'viewer',
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: null,
        group_ids: [],
      })
    );
  });

  it('sub admin create payload clears manager user and requires managed root', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-company'));
    await user.click(screen.getByTestId('set-department'));
    await user.click(screen.getByTestId('set-manager'));
    await user.click(screen.getByTestId('set-type-sub-admin'));
    await user.click(screen.getByTestId('submit-create'));

    await waitFor(() => {
      expect(screen.getByTestId('create-error')).toHaveTextContent('请选择子管理员负责的知识库目录');
    });
    expect(usersApi.create).not.toHaveBeenCalled();
  });

  it('sub admin create payload keeps selected permission groups', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-company'));
    await user.click(screen.getByTestId('set-department'));
    await user.click(screen.getByTestId('set-type-sub-admin'));
    await user.click(screen.getByTestId('select-create-group-7'));
    await user.click(screen.getByTestId('set-create-root-node'));
    await user.click(screen.getByTestId('submit-create'));

    await waitFor(() => expect(usersApi.create).toHaveBeenCalled());
    expect(usersApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        role: 'sub_admin',
        group_ids: [7],
      })
    );
  });

  it('editing viewer requires manager user and clears direct groups', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-policy-normal'));
    await user.click(screen.getByTestId('policy-set-normal-empty-manager'));
    await user.click(screen.getByTestId('submit-policy'));

    await waitFor(() => {
      expect(screen.getByTestId('policy-error')).toHaveTextContent('请选择归属子管理员');
    });
    expect(usersApi.update).not.toHaveBeenCalled();
  });

  it('editing sub admin to normal user requires manager and clears managed root', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-policy-sub-admin'));
    await user.click(screen.getByTestId('policy-set-normal'));
    await user.click(screen.getByTestId('submit-policy'));

    await waitFor(() => expect(usersApi.update).toHaveBeenCalled());
    expect(usersApi.update).toHaveBeenCalledWith(
      'u-2',
      expect.objectContaining({
        role: 'viewer',
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: null,
        group_ids: [],
      })
    );
  });

  it('editing sub admin keeps selected permission groups', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-policy-sub-admin'));
    await user.click(screen.getByTestId('submit-policy'));

    await waitFor(() => expect(usersApi.update).toHaveBeenCalled());
    expect(usersApi.update).toHaveBeenCalledWith(
      'u-2',
      expect.objectContaining({
        role: 'sub_admin',
        group_ids: [7],
      })
    );
  });

  it('blocks submit when departments cannot be loaded', async () => {
    orgDirectoryApi.listDepartments.mockResolvedValueOnce([]);
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => {
      expect(screen.getByTestId('org-error')).toHaveTextContent('组织管理中没有可用部门，无法创建或编辑用户');
    });
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('submit-create'));

    await waitFor(() => {
      expect(screen.getByTestId('create-error')).toHaveTextContent('组织管理中没有可用部门，无法创建或编辑用户');
    });
    expect(usersApi.create).not.toHaveBeenCalled();
  });

  it('only sub admin can assign groups and only for owned users', async () => {
    useAuth.mockReturnValue({
      user: { role: 'sub_admin', user_id: 'sub-actor' },
      can: jest.fn(() => true),
    });
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    expect(screen.getByTestId('assign-groups-flag')).toHaveTextContent('yes');

    await user.click(screen.getByTestId('assign-other-user'));
    expect(screen.getByTestId('show-group-modal')).toHaveTextContent('no');

    await user.click(screen.getByTestId('assign-owned-user'));
    expect(screen.getByTestId('show-group-modal')).toHaveTextContent('yes');
  });

  it('filters stale permission group ids before saving owned user assignments', async () => {
    useAuth.mockReturnValue({
      user: { role: 'sub_admin', user_id: 'sub-actor' },
      can: jest.fn(() => true),
    });
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await waitFor(() => expect(permissionGroupsApi.listAssignable).toHaveBeenCalled());

    await user.click(screen.getByTestId('assign-owned-user-stale-groups'));

    expect(screen.getByTestId('show-group-modal')).toHaveTextContent('yes');
    expect(screen.getByTestId('selected-group-ids')).toHaveTextContent('7');

    await user.click(screen.getByTestId('save-group'));

    await waitFor(() =>
      expect(usersApi.update).toHaveBeenCalledWith('u-owned-stale', { group_ids: [7] })
    );
  });

  it('admin loads assignable permission groups for sub admin configuration', async () => {
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await waitFor(() => expect(permissionGroupsApi.listAssignable).toHaveBeenCalled());
  });

  it('sub admin still loads permission groups for assignment', async () => {
    useAuth.mockReturnValue({
      user: { role: 'sub_admin', user_id: 'sub-actor' },
      can: jest.fn(() => true),
    });

    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await waitFor(() => expect(permissionGroupsApi.listAssignable).toHaveBeenCalled());
  });

  it('sub admin can reset own and owned user passwords only', async () => {
    useAuth.mockReturnValue({
      user: { role: 'sub_admin', user_id: 'sub-actor' },
      can: jest.fn(() => true),
    });
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    expect(screen.getByTestId('reset-passwords-flag')).toHaveTextContent('yes');

    await user.click(screen.getByTestId('open-reset-other-viewer'));
    expect(screen.getByTestId('show-reset-password-modal')).toHaveTextContent('no');

    await user.click(screen.getByTestId('open-reset-owned'));
    expect(screen.getByTestId('show-reset-password-modal')).toHaveTextContent('yes');

    await user.click(screen.getByTestId('close-reset'));
    expect(screen.getByTestId('show-reset-password-modal')).toHaveTextContent('no');

    await user.click(screen.getByTestId('open-reset-other-sub-admin'));
    expect(screen.getByTestId('show-reset-password-modal')).toHaveTextContent('no');

    await user.click(screen.getByTestId('open-reset-self'));
    expect(screen.getByTestId('show-reset-password-modal')).toHaveTextContent('yes');
  });

  it('reloads knowledge directories by selected company for sub admin creation', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    knowledgeApi.listKnowledgeDirectories.mockClear();

    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-type-sub-admin'));
    await user.click(screen.getByTestId('set-company'));

    await waitFor(() =>
      expect(knowledgeApi.listKnowledgeDirectories).toHaveBeenCalledWith({ companyId: 1 })
    );

    await user.click(screen.getByTestId('set-company-2'));

    await waitFor(() =>
      expect(knowledgeApi.listKnowledgeDirectories).toHaveBeenCalledWith({ companyId: 2 })
    );
  });

  it('admin can create a top-level root directory for the selected company', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-type-sub-admin'));
    await user.click(screen.getByTestId('set-company'));
    await user.click(screen.getByTestId('create-root-create'));

    await waitFor(() =>
      expect(knowledgeApi.createKnowledgeDirectory).toHaveBeenCalledWith(
        { name: 'New Root', parent_id: null },
        { companyId: 1 }
      )
    );
  });

  it('marks invalid managed root and blocks saving until rebinding', async () => {
    const user = userEvent.setup();
    knowledgeApi.listKnowledgeDirectories.mockResolvedValueOnce({ nodes: [], datasets: [] });

    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-policy-sub-admin'));

    await waitFor(() => {
      expect(screen.getByTestId('kb-root-invalid')).toHaveTextContent('yes');
    });

    await user.click(screen.getByTestId('submit-policy'));

    await waitFor(() => {
      expect(screen.getByTestId('policy-error')).toHaveTextContent('当前负责目录已失效');
    });
    expect(usersApi.update).not.toHaveBeenCalled();
  });
});
