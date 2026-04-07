import React from 'react';
import CreateUserModal from './modals/CreateUserModal';
import ResetPasswordModal from './modals/ResetPasswordModal';
import PolicyModal from './modals/PolicyModal';
import GroupModal from './modals/GroupModal';
import DisableUserModal from './modals/DisableUserModal';

const UserManagementModals = ({
  canCreateUsers,
  showCreateModal,
  newUser,
  createUserError,
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
  subAdminOptions,
  policySubAdminOptions,
  handleChangePolicyForm,
  setResetPasswordValue,
  setResetPasswordConfirm,
  handleCloseCreateModal,
  setNewUserField,
  toggleNewUserGroup,
  handleCreateUser,
  handleCloseResetPassword,
  handleSubmitResetPassword,
  handleClosePolicyModal,
  handleTogglePolicyGroup,
  handleSavePolicy,
  handleCloseDisableUserModal,
  handleChangeDisableMode,
  handleChangeDisableUntilDate,
  handleConfirmDisableUser,
  handleCloseGroupModal,
  toggleSelectedGroup,
  handleSaveGroup,
  handleCreateModalRootDirectory,
  handlePolicyRootDirectory,
}) => (
  <>
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
  </>
);

export default UserManagementModals;
