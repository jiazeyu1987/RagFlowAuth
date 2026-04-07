import React from 'react';
import UserFiltersPanel from './UserFiltersPanel';
import DepartmentCards from './DepartmentCards';
import UsersTable from './UsersTable';

const UserManagementContent = ({
  isMobile,
  canCreateUsers,
  isSubAdminUser,
  filteredUsers,
  canManageUsers,
  canEditUserPolicy,
  canAssignGroups,
  canResetPasswords,
  canResetPasswordForUser,
  canToggleUserStatus,
  canDeleteUsers,
  statusUpdatingUserId,
  filters,
  companies,
  departments,
  availableGroups,
  permissionGroupsLoading,
  permissionGroupsError,
  groupedUsers,
  setFilters,
  handleLoadPermissionGroups,
  handleOpenCreateModal,
  handleOpenPolicyModal,
  handleAssignGroup,
  handleOpenResetPassword,
  handleDeleteUser,
  handleToggleUserStatus,
  handleResetFilters,
}) => (
  <>
    {canCreateUsers ? (
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: isMobile ? 'stretch' : 'center',
          marginBottom: '24px',
        }}
      >
        <button
          type="button"
          onClick={handleOpenCreateModal}
          data-testid="users-create-open"
          style={{
            padding: '10px 20px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          创建用户
        </button>
      </div>
    ) : null}

    <div
      data-testid="users-management-layout"
      style={{
        display: 'flex',
        flexDirection: isMobile ? 'column-reverse' : 'row',
        gap: '16px',
        alignItems: 'flex-start',
      }}
    >
      <div
        data-testid="users-management-list-column"
        style={{
          flex: '1 1 0%',
          minWidth: 0,
          width: '100%',
        }}
      >
        <UsersTable
          filteredUsers={filteredUsers}
          canManageUsers={canManageUsers}
          canEditUserPolicy={canEditUserPolicy}
          canAssignGroups={canAssignGroups}
          canResetPasswords={canResetPasswords}
          canResetPasswordForUser={canResetPasswordForUser}
          canToggleUserStatus={canToggleUserStatus}
          canDeleteUsers={canDeleteUsers}
          onOpenPolicyModal={handleOpenPolicyModal}
          onAssignGroup={handleAssignGroup}
          onOpenResetPassword={handleOpenResetPassword}
          onDeleteUser={handleDeleteUser}
          onToggleUserStatus={handleToggleUserStatus}
          statusUpdatingUserId={statusUpdatingUserId}
        />
      </div>

      <div
        data-testid="users-management-side-column"
        style={{
          flex: isMobile ? '1 1 auto' : '0 0 360px',
          width: isMobile ? '100%' : '360px',
          maxWidth: '100%',
          minWidth: 0,
        }}
      >
        <UserFiltersPanel
          filters={filters}
          setFilters={setFilters}
          companies={companies}
          departments={departments}
          availableGroups={availableGroups}
          permissionGroupsLoading={permissionGroupsLoading}
          permissionGroupsError={permissionGroupsError}
          isSubAdminUser={isSubAdminUser}
          onGroupFilterFocus={handleLoadPermissionGroups}
          onResetFilters={handleResetFilters}
        />

        {isSubAdminUser ? null : (
          <DepartmentCards
            filteredUsers={filteredUsers}
            groupedUsers={groupedUsers}
            filters={filters}
            setFilters={setFilters}
          />
        )}
      </div>
    </div>
  </>
);

export default UserManagementContent;
