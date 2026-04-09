import React from 'react';
import CreateUserModal from './modals/CreateUserModal';
import ResetPasswordModal from './modals/ResetPasswordModal';
import PolicyModal from './modals/PolicyModal';
import GroupModal from './modals/GroupModal';
import ToolModal from './modals/ToolModal';
import DisableUserModal from './modals/DisableUserModal';

const UserManagementModals = ({
  canCreateUsers,
  allUsers,
  showCreateModal,
  newUser,
  createUserError,
  availableGroups,
  availableTools,
  assignableTools,
  permissionGroupsLoading,
  permissionGroupsError,
  editingGroupUser,
  showGroupModal,
  selectedGroupIds,
  editingToolUser,
  showToolModal,
  selectedToolIds,
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
  toggleNewUserTool,
  handleCreateUser,
  handleCloseResetPassword,
  handleSubmitResetPassword,
  handleClosePolicyModal,
  handleTogglePolicyGroup,
  handleTogglePolicyTool,
  handleSavePolicy,
  handleCloseDisableUserModal,
  handleChangeDisableMode,
  handleChangeDisableUntilDate,
  handleConfirmDisableUser,
  handleCloseGroupModal,
  toggleSelectedGroup,
  handleSaveGroup,
  handleCloseToolModal,
  toggleSelectedTool,
  handleSaveTool,
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
      availableTools={availableTools}
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
      onToggleTool={handleTogglePolicyTool}
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
        allUsers={allUsers}
        companies={companies}
        departments={departments}
        subAdminOptions={subAdminOptions}
        availableTools={availableTools}
        kbDirectoryNodes={kbDirectoryNodes}
        kbDirectoryLoading={kbDirectoryLoading}
        kbDirectoryError={kbDirectoryError}
        kbDirectoryCreateError={kbDirectoryCreateError}
        kbDirectoryCreatingRoot={kbDirectoryCreatingRoot}
        orgDirectoryError={orgDirectoryError}
        onSubmit={handleCreateUser}
        onCancel={handleCloseCreateModal}
        onFieldChange={setNewUserField}
        onToggleTool={toggleNewUserTool}
        onCreateRootDirectory={handleCreateModalRootDirectory}
      />
    ) : null}

    <GroupModal
      open={showGroupModal}
      editingGroupUser={editingGroupUser}
      availableGroups={availableGroups}
      permissionGroupsLoading={permissionGroupsLoading}
      permissionGroupsError={permissionGroupsError}
      selectedGroupIds={selectedGroupIds}
      onToggleGroup={toggleSelectedGroup}
      onCancel={handleCloseGroupModal}
      onSave={handleSaveGroup}
    />

    <ToolModal
      open={showToolModal}
      editingToolUser={editingToolUser}
      availableTools={assignableTools}
      selectedToolIds={selectedToolIds}
      onToggleTool={toggleSelectedTool}
      onCancel={handleCloseToolModal}
      onSave={handleSaveTool}
    />
  </>
);

export default UserManagementModals;
