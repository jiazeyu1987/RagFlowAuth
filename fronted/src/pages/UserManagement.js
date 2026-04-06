import React from 'react';
import UserFiltersPanel from '../features/users/components/UserFiltersPanel';
import DepartmentCards from '../features/users/components/DepartmentCards';
import UsersTable from '../features/users/components/UsersTable';
import CreateUserModal from '../features/users/components/modals/CreateUserModal';
import ResetPasswordModal from '../features/users/components/modals/ResetPasswordModal';
import PolicyModal from '../features/users/components/modals/PolicyModal';
import GroupModal from '../features/users/components/modals/GroupModal';
import DisableUserModal from '../features/users/components/modals/DisableUserModal';
import useUserManagementPage from '../features/users/useUserManagementPage';

const UserManagement = () => {
  const {
    isMobile,
    loading,
    error,
    isSubAdminUser,
    canManageUsers,
    canCreateUsers,
    canEditUserPolicy,
    canResetPasswords,
    canResetPasswordForUser,
    canToggleUserStatus,
    canDeleteUsers,
    canAssignGroups,
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
    orgDirectoryError,
    kbDirectoryNodes,
    kbDirectoryLoading,
    kbDirectoryError,
    kbDirectoryCreateError,
    kbDirectoryCreatingRoot,
    managedKbRootInvalid,
    filteredUsers,
    groupedUsers,
    subAdminOptions,
    policySubAdminOptions,
    setFilters,
    handleChangePolicyForm,
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
    handleTogglePolicyGroup,
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
    handleCreateModalRootDirectory,
    handlePolicyRootDirectory,
  } = useUserManagementPage();

  if (loading) return <div>鍔犺浇涓?..</div>;
  if (error) return <div>閿欒: {error}</div>;

  return (
    <div>
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
            鏂板缓鐢ㄦ埛
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
            isSubAdminUser={isSubAdminUser}
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
        companies={companies}
        departments={departments}
        policySubAdminOptions={policySubAdminOptions}
        availableGroups={availableGroups}
        kbDirectoryNodes={kbDirectoryNodes}
        kbDirectoryLoading={kbDirectoryLoading}
        kbDirectoryError={kbDirectoryError}
        kbDirectoryCreateError={kbDirectoryCreateError}
        kbDirectoryCreatingRoot={kbDirectoryCreatingRoot}
        managedKbRootInvalid={managedKbRootInvalid}
        orgDirectoryError={orgDirectoryError}
        policyError={policyError}
        policySubmitting={policySubmitting}
        onChangePolicyForm={handleChangePolicyForm}
        onToggleGroup={handleTogglePolicyGroup}
        onCancel={handleClosePolicyModal}
        onSave={handleSavePolicy}
        onCreateRootDirectory={handlePolicyRootDirectory}
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

      {canCreateUsers ? (
        <CreateUserModal
          open={showCreateModal}
          newUser={newUser}
          error={createUserError}
          companies={companies}
          departments={departments}
          subAdminOptions={subAdminOptions}
          availableGroups={availableGroups}
          kbDirectoryNodes={kbDirectoryNodes}
          kbDirectoryLoading={kbDirectoryLoading}
          kbDirectoryError={kbDirectoryError}
          kbDirectoryCreateError={kbDirectoryCreateError}
          kbDirectoryCreatingRoot={kbDirectoryCreatingRoot}
          orgDirectoryError={orgDirectoryError}
          onSubmit={handleCreateUser}
          onCancel={handleCloseCreateModal}
          onFieldChange={setNewUserField}
          onToggleGroup={toggleNewUserGroup}
          onCreateRootDirectory={handleCreateModalRootDirectory}
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
