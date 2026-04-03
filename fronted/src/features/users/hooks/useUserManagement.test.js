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
    list: jest.fn(),
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
  },
}));

function HookHarness() {
  const hook = useUserManagement();
  return (
    <div>
      <button type="button" data-testid="open-create" onClick={hook.handleOpenCreateModal}>
        open-create
      </button>
      <button type="button" data-testid="set-role-sub-admin" onClick={() => hook.setNewUserField('role', 'sub_admin')}>
        set-role-sub-admin
      </button>
      <button type="button" data-testid="set-role-viewer" onClick={() => hook.setNewUserField('role', 'viewer')}>
        set-role-viewer
      </button>
      <button type="button" data-testid="set-root-node" onClick={() => hook.setNewUserField('managed_kb_root_node_id', 'node-1')}>
        set-root-node
      </button>
      <button type="button" data-testid="submit-create" onClick={() => hook.handleCreateUser({ preventDefault() {} })}>
        submit-create
      </button>
      <button
        type="button"
        data-testid="open-policy"
        onClick={() =>
          hook.handleOpenPolicyModal({
            user_id: 'u-1',
            username: 'alice',
            role: 'sub_admin',
            full_name: 'Alice',
            email: 'alice@example.com',
            company_id: 1,
            department_id: 11,
            group_ids: [7],
            managed_kb_root_node_id: 'node-1',
            max_login_sessions: 3,
            idle_timeout_minutes: 120,
            can_change_password: true,
            status: 'active',
          })
        }
      >
        open-policy
      </button>
      <button
        type="button"
        data-testid="policy-role-viewer"
        onClick={() => hook.setPolicyForm((prev) => ({ ...prev, role: 'viewer', managed_kb_root_node_id: 'node-1' }))}
      >
        policy-role-viewer
      </button>
      <button
        type="button"
        data-testid="policy-role-sub-admin-empty"
        onClick={() => hook.setPolicyForm((prev) => ({ ...prev, role: 'sub_admin', managed_kb_root_node_id: '' }))}
      >
        policy-role-sub-admin-empty
      </button>
      <button type="button" data-testid="submit-policy" onClick={hook.handleSavePolicy}>
        submit-policy
      </button>
      <div data-testid="create-error">{hook.createUserError || ''}</div>
      <div data-testid="policy-error">{hook.policyError || ''}</div>
    </div>
  );
}

describe('useUserManagement sub admin payloads', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: { role: 'admin' },
      can: jest.fn(() => true),
    });
    usersApi.list.mockResolvedValue([]);
    usersApi.create.mockResolvedValue({});
    usersApi.update.mockResolvedValue({});
    permissionGroupsApi.list.mockResolvedValue({ ok: true, data: [{ group_id: 7, group_name: 'G7' }] });
    orgDirectoryApi.listCompanies.mockResolvedValue([{ id: 1, name: 'Acme' }]);
    orgDirectoryApi.listDepartments.mockResolvedValue([{ id: 11, name: 'QA', company_id: 1 }]);
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [{ id: 'node-1', name: '目录A', parent_id: '', path: '/目录A' }],
      datasets: [],
    });
  });

  it('requires managed root when creating sub admin', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-role-sub-admin'));
    await user.click(screen.getByTestId('submit-create'));

    await waitFor(() => {
      expect(screen.getByTestId('create-error')).toHaveTextContent('请选择子管理员负责的知识库目录');
    });
    expect(usersApi.create).not.toHaveBeenCalled();
  });

  it('clears managed root when creating non sub admin', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-create'));
    await user.click(screen.getByTestId('set-root-node'));
    await user.click(screen.getByTestId('set-role-viewer'));
    await user.click(screen.getByTestId('submit-create'));

    await waitFor(() => expect(usersApi.create).toHaveBeenCalled());
    expect(usersApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        role: 'viewer',
        managed_kb_root_node_id: null,
      })
    );
  });

  it('clears managed root when editing user away from sub admin', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-policy'));
    await user.click(screen.getByTestId('policy-role-viewer'));
    await user.click(screen.getByTestId('submit-policy'));

    await waitFor(() => expect(usersApi.update).toHaveBeenCalled());
    expect(usersApi.update).toHaveBeenCalledWith(
      'u-1',
      expect.objectContaining({
        role: 'viewer',
        managed_kb_root_node_id: null,
      })
    );
  });

  it('requires managed root when editing user into sub admin', async () => {
    const user = userEvent.setup();
    render(<HookHarness />);

    await waitFor(() => expect(usersApi.list).toHaveBeenCalled());
    await user.click(screen.getByTestId('open-policy'));
    await user.click(screen.getByTestId('policy-role-sub-admin-empty'));
    await user.click(screen.getByTestId('submit-policy'));

    await waitFor(() => {
      expect(screen.getByTestId('policy-error')).toHaveTextContent('请选择子管理员负责的知识库目录');
    });
    expect(usersApi.update).not.toHaveBeenCalled();
  });
});
