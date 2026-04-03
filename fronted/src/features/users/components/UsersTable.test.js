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
            email: 'a@example.com',
            role: 'sub_admin',
            company_name: 'Acme',
            department_name: 'QA',
            managed_kb_root_path: '/研发知识库/一组',
            status: 'active',
          },
        ]}
        canManageUsers
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

    expect(screen.getByTestId('users-role-u-sub-1')).toBeInTheDocument();
    expect(screen.getByTestId('users-managed-root-u-sub-1')).toHaveTextContent('KB 子树管理员');
    expect(screen.getByTestId('users-managed-root-u-sub-1')).toHaveTextContent('/研发知识库/一组');
    expect(screen.getByTestId('users-edit-policy-u-sub-1')).toHaveTextContent('用户配置');
  });
});
