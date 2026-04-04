import React from 'react';
import { render, screen } from '@testing-library/react';
import UsersTable from './UsersTable';

describe('UsersTable', () => {
  it('renders assigned permission groups and hides group assignment for sub admins', () => {
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
            permission_groups: [
              { group_id: 1, group_name: '研发资料组' },
              { group_id: 2, group_name: '审核流程组' },
            ],
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

    expect(screen.getByTestId('users-permission-groups-u-sub-1')).toHaveTextContent('研发资料组');
    expect(screen.getByTestId('users-permission-groups-u-sub-1')).toHaveTextContent('审核流程组');
    expect(screen.queryByTestId('users-edit-groups-u-sub-1')).not.toBeInTheDocument();
  });

  it('shows pending assignment in red when a viewer has no permission groups', () => {
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
            permission_groups: [],
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

    expect(screen.getByTestId('users-permission-groups-empty-u-viewer-1')).toHaveTextContent('待分配');
    expect(screen.getByTestId('users-permission-groups-empty-u-viewer-1')).toHaveStyle({
      color: '#b91c1c',
    });
    expect(screen.getByTestId('users-edit-groups-u-viewer-1')).toBeInTheDocument();
  });

  it('shows reset password only for rows allowed by the row-level guard', () => {
    render(
      <UsersTable
        filteredUsers={[
          {
            user_id: 'u-allowed',
            username: 'viewer_a',
            full_name: 'Viewer A',
            role: 'viewer',
            status: 'active',
          },
          {
            user_id: 'u-denied',
            username: 'sub_admin_b',
            full_name: 'Sub Admin B',
            role: 'sub_admin',
            status: 'active',
          },
        ]}
        canEditUserPolicy={false}
        canAssignGroups={false}
        canResetPasswords
        canResetPasswordForUser={(user) => user.user_id === 'u-allowed'}
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

    expect(screen.getByTestId('users-reset-password-u-allowed')).toBeInTheDocument();
    expect(screen.queryByTestId('users-reset-password-u-denied')).not.toBeInTheDocument();
  });
});
