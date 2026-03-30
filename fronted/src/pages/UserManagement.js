import React, { useEffect, useState } from 'react';
import UserFiltersPanel from '../features/users/components/UserFiltersPanel';
import DepartmentCards from '../features/users/components/DepartmentCards';
import UsersTable from '../features/users/components/UsersTable';
import CreateUserModal from '../features/users/components/modals/CreateUserModal';
import ResetPasswordModal from '../features/users/components/modals/ResetPasswordModal';
import PolicyModal from '../features/users/components/modals/PolicyModal';
import GroupModal from '../features/users/components/modals/GroupModal';
import DisableUserModal from '../features/users/components/modals/DisableUserModal';
import { useUserManagement } from '../features/users/hooks/useUserManagement';

const MOBILE_BREAKPOINT = 768;

const UserManagement = () => {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  const {
    loading,
    error,
    canManageUsers,
    showCreateModal,
    newUser,
    createUserError,
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
    showDisableUserModal,
    disableTargetUser,
    disableMode,
    disableUntilDate,
    disableUserError,
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
    handleCloseDisableUserModal,
    handleChangeDisableMode,
    handleChangeDisableUntilDate,
    handleConfirmDisableUser,
    handleAssignGroup,
    handleCloseGroupModal,
    toggleSelectedGroup,
    handleSaveGroup,
    handleResetFilters,
  } = useUserManagement();

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (loading) return <div>加载中...</div>;
  if (error) return <div>错误: {error}</div>;

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'center',
          flexDirection: isMobile ? 'column' : 'row',
          gap: isMobile ? '12px' : 0,
          marginBottom: '24px',
        }}
      >
        <h2 style={{ margin: 0 }}>用户管理</h2>
        {canManageUsers ? (
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
            新建用户
          </button>
        ) : null}
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

      <DisableUserModal
        open={showDisableUserModal}
        user={disableTargetUser}
        mode={disableMode}
        untilDate={disableUntilDate}
        error={disableUserError}
        submitting={!!statusUpdatingUserId}
        onChangeMode={handleChangeDisableMode}
        onChangeUntilDate={handleChangeDisableUntilDate}
        onCancel={handleCloseDisableUserModal}
        onConfirm={handleConfirmDisableUser}
      />

      {canManageUsers ? (
        <CreateUserModal
          open={showCreateModal}
          newUser={newUser}
          error={createUserError}
          availableGroups={availableGroups}
          companies={companies}
          departments={departments}
          onSubmit={handleCreateUser}
          onCancel={handleCloseCreateModal}
          onFieldChange={setNewUserField}
          onToggleGroup={toggleNewUserGroup}
        />
      ) : null}

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
