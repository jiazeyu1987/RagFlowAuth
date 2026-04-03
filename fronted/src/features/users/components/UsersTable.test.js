import React from 'react';
import { render, screen } from '@testing-library/react';
import UsersTable from './UsersTable';

describe('UsersTable', () => {
  it('renders sub admin role badge and managed root path clearly', () => {
    render(
      <UsersTable
        filteredUsers={[
          {
            user_id: 'u-sub-1',
            username: 'sub_admin_a',
            full_name: '子管理员A',
            role: 'sub_admin',
            company_name: 'Acme',
            department_name: 'QA',
            managed_kb_root_path: '/研发知识库/一组',
            status: 'active',
          },
        ]}
        canEditUserPolicy
        canAssignGroups
        canResetPasswords
        canToggleUserStatus
        canDeleteUsers
        onOpenPolicyModal={() => {}}
        onAssignGroup={() => {}}
        onOpenResetPassword={() => {}}
        onDeleteUser={() => {}}
        onToggleUserStatus={() => {}}
        statusUpdatingUserId=""
      />
    );

    expect(screen.getByTestId('users-role-u-sub-1')).toHaveTextContent('子管理员');
    expect(screen.getByTestId('users-managed-root-u-sub-1')).toHaveTextContent('KB 子树管理员');
    expect(screen.getByTestId('users-managed-root-u-sub-1')).toHaveTextContent('/研发知识库/一组');
    expect(screen.queryByTestId('users-edit-groups-u-sub-1')).not.toBeInTheDocument();
  });

  it('renders viewer owner info and group button only when allowed', () => {
    render(
      <UsersTable
        filteredUsers={[
          {
            user_id: 'u-viewer-1',
            username: 'viewer_a',
            full_name: '普通用户A',
            role: 'viewer',
            company_name: 'Acme',
            department_name: 'QA',
            manager_username: 'sub_admin_a',
            manager_full_name: '子管理员A',
            manager_user_id: 'sub-1',
            status: 'active',
          },
        ]}
        canEditUserPolicy
        canAssignGroups
        canResetPasswords={false}
        canToggleUserStatus={false}
        canDeleteUsers={false}
        onOpenPolicyModal={() => {}}
        onAssignGroup={() => {}}
        onOpenResetPassword={() => {}}
        onDeleteUser={() => {}}
        onToggleUserStatus={() => {}}
        statusUpdatingUserId=""
      />
    );

    expect(screen.getByTestId('users-owned-by-u-viewer-1')).toHaveTextContent('归属子管理员');
    expect(screen.getByTestId('users-owned-by-u-viewer-1')).toHaveTextContent('子管理员A(sub_admin_a)');
    expect(screen.getByTestId('users-edit-groups-u-viewer-1')).toBeInTheDocument();
  });
});
