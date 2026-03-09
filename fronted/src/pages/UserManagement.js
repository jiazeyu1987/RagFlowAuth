import React from 'react';
import UserFiltersPanel from '../features/users/components/UserFiltersPanel';
import DepartmentCards from '../features/users/components/DepartmentCards';
import UsersTable from '../features/users/components/UsersTable';
import CreateUserModal from '../features/users/components/modals/CreateUserModal';
import ResetPasswordModal from '../features/users/components/modals/ResetPasswordModal';
import PolicyModal from '../features/users/components/modals/PolicyModal';
import GroupModal from '../features/users/components/modals/GroupModal';
import { useUserManagement } from '../features/users/hooks/useUserManagement';

const UserManagement = () => {
  const {
    loading,
    error,
    canManageUsers,
    showCreateModal,
    newUser,
    filters,
    availableGroups,
    editingGroupUser,
    showGroupModal,
    selectedGroupIds,
    showResetPasswordModal,
    resetPasswordUser,
    resetPasswordValue,
    resetPasswordConfirm,
    resetPasswordSubmitting,
    resetPasswordError,
    showPolicyModal,
    policyUser,
    policySubmitting,
    policyError,
    policyForm,
    statusUpdatingUserId,
    companies,
    departments,
    filteredUsers,
    groupedUsers,
    setFilters,
    setPolicyForm,
    setResetPasswordValue,
    setResetPasswordConfirm,
    handleOpenCreateModal,
    handleCloseCreateModal,
    setNewUserField,
    toggleNewUserGroup,
    handleCreateUser,
    handleDeleteUser,
    handleToggleUserStatus,
    handleOpenResetPassword,
    handleCloseResetPassword,
    handleSubmitResetPassword,
    handleOpenPolicyModal,
    handleClosePolicyModal,
    handleSavePolicy,
    handleAssignGroup,
    handleCloseGroupModal,
    toggleSelectedGroup,
    handleSaveGroup,
    handleResetFilters,
  } = useUserManagement();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: 0 }}>{'用户管理'}</h2>
        {canManageUsers && (
          <button
            onClick={handleOpenCreateModal}
            data-testid="users-create-open"
            style={{
              padding: '10px 20px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {'新建用户'}
          </button>
        )}
      </div>

      <UserFiltersPanel
        filters={filters}
        setFilters={setFilters}
        companies={companies}
        departments={departments}
        availableGroups={availableGroups}
        onResetFilters={handleResetFilters}
      />

      <DepartmentCards
        filteredUsers={filteredUsers}
        groupedUsers={groupedUsers}
        filters={filters}
        setFilters={setFilters}
      />

      <UsersTable
        filteredUsers={filteredUsers}
        canManageUsers={canManageUsers}
        onOpenPolicyModal={handleOpenPolicyModal}
        onAssignGroup={handleAssignGroup}
        onOpenResetPassword={handleOpenResetPassword}
        onDeleteUser={handleDeleteUser}
        onToggleUserStatus={handleToggleUserStatus}
        statusUpdatingUserId={statusUpdatingUserId}
      />

      <ResetPasswordModal
        open={showResetPasswordModal}
        user={resetPasswordUser}
        value={resetPasswordValue}
        confirm={resetPasswordConfirm}
        error={resetPasswordError}
        submitting={resetPasswordSubmitting}
        onChangeValue={setResetPasswordValue}
        onChangeConfirm={setResetPasswordConfirm}
        onCancel={handleCloseResetPassword}
        onSubmit={handleSubmitResetPassword}
      />

      <PolicyModal
        open={showPolicyModal}
        user={policyUser}
        policyForm={policyForm}
        policyError={policyError}
        policySubmitting={policySubmitting}
        onChangePolicyForm={setPolicyForm}
        onCancel={handleClosePolicyModal}
        onSave={handleSavePolicy}
      />

      {canManageUsers && (
        <CreateUserModal
          open={showCreateModal}
          newUser={newUser}
          availableGroups={availableGroups}
          companies={companies}
          departments={departments}
          onSubmit={handleCreateUser}
          onCancel={handleCloseCreateModal}
          onFieldChange={setNewUserField}
          onToggleGroup={toggleNewUserGroup}
        />
      )}

      <GroupModal
        open={showGroupModal}
        editingGroupUser={editingGroupUser}
        availableGroups={availableGroups}
        selectedGroupIds={selectedGroupIds}
        onToggleGroup={toggleSelectedGroup}
        onCancel={handleCloseGroupModal}
        onSave={handleSaveGroup}
      />
    </div>
  );
};

export default UserManagement;
