import { useEffect } from 'react';
import { useAuth } from '../../../hooks/useAuth';
import {
  LOAD_KNOWLEDGE_DIRECTORIES_ERROR,
  ROOT_DIRECTORY_COMPANY_REQUIRED_MESSAGE,
  ROOT_DIRECTORY_NAME_REQUIRED_MESSAGE,
  mapUserManagementErrorMessage,
  CREATE_ROOT_DIRECTORY_ERROR,
} from '../utils/userManagementMessages';
import { useUserKnowledgeDirectories } from './useUserKnowledgeDirectories';
import { useUserManagementData } from './useUserManagementData';
import { useUserPasswordReset } from './useUserPasswordReset';
import { useUserGroupAssignment } from './useUserGroupAssignment';
import { useUserPolicyManagement } from './useUserPolicyManagement';
import { useUserStatusManagement } from './useUserStatusManagement';
import { useUserCreateManagement } from './useUserCreateManagement';
import { useUserManagementViewModel } from './useUserManagementViewModel';
import { useUserDeletion } from './useUserDeletion';
import { useUserManagementActions } from './useUserManagementActions';
import { buildUserManagementCapabilities } from '../utils/userManagementCapabilities';
import { buildUserKnowledgeDirectoryModes } from '../utils/userKnowledgeDirectoryModes';
import { buildUserManagementState } from '../utils/userManagementState';

export const useUserManagement = () => {
  const { can, user } = useAuth();
  const capabilities = buildUserManagementCapabilities(user);

  const {
    allUsers,
    loading,
    error,
    canManageUsers,
    availableGroups,
    permissionGroupsLoading,
    permissionGroupsError,
    companies,
    departments,
    orgDirectoryError,
    fetchUsers,
    fetchPermissionGroups,
    setError,
  } = useUserManagementData({
    can,
    isAdminUser: capabilities.isAdminUser,
    isSubAdminUser: capabilities.isSubAdminUser,
  });

  const policyManagement = useUserPolicyManagement({
    departments,
  });

  const createManagement = useUserCreateManagement({
    departments,
    fetchUsers,
    mapErrorMessage: mapUserManagementErrorMessage,
  });

  const knowledgeDirectoryModes = buildUserKnowledgeDirectoryModes({
    createManagement,
    policyManagement,
  });

  const {
    filters,
    setFilters,
    filteredUsers,
    groupedUsers,
    subAdminOptions,
    policySubAdminOptions,
    handleResetFilters,
  } = useUserManagementViewModel({
    allUsers,
    createCompanyId: createManagement.newUser.company_id,
    policyCompanyId: policyManagement.policyForm.company_id,
    policyUserId: policyManagement.policyUser?.user_id,
  });

  const {
    kbDirectoryNodes,
    kbDirectoryLoading,
    kbDirectoryError,
    kbDirectoryCreatingRoot,
    kbDirectoryCreateError,
    managedKbRootInvalid,
    clearKbDirectoryCreateError,
    handleCreateModalRootDirectory,
    handlePolicyRootDirectory,
  } = useUserKnowledgeDirectories({
    isAdminUser: capabilities.isAdminUser,
    createMode: knowledgeDirectoryModes.createMode,
    policyMode: knowledgeDirectoryModes.policyMode,
    policyUser: policyManagement.policyUser,
    mapErrorMessage: mapUserManagementErrorMessage,
    companyRequiredMessage: ROOT_DIRECTORY_COMPANY_REQUIRED_MESSAGE,
    nameRequiredMessage: ROOT_DIRECTORY_NAME_REQUIRED_MESSAGE,
    loadErrorMessage: LOAD_KNOWLEDGE_DIRECTORIES_ERROR,
    createErrorMessage: CREATE_ROOT_DIRECTORY_ERROR,
  });

  const actions = useUserManagementActions({
    createManagement,
    policyManagement,
    kbDirectoryNodes,
    orgDirectoryError,
    clearKbDirectoryCreateError,
    fetchUsers,
    mapErrorMessage: mapUserManagementErrorMessage,
  });

  const passwordReset = useUserPasswordReset({
    actorRole: capabilities.actorRole,
    actorUserId: capabilities.actorUserId,
    mapErrorMessage: mapUserManagementErrorMessage,
  });

  const groupAssignment = useUserGroupAssignment({
    actorRole: capabilities.actorRole,
    actorUserId: capabilities.actorUserId,
    availableGroups,
    ensureAvailableGroupsLoaded: fetchPermissionGroups,
    mapErrorMessage: mapUserManagementErrorMessage,
    onError: setError,
    onSaved: fetchUsers,
  });

  useEffect(() => {
    if (
      createManagement.showCreateModal
      && String(createManagement.newUser.user_type || 'normal') === 'sub_admin'
    ) {
      fetchPermissionGroups();
    }
  }, [
    createManagement.newUser.user_type,
    createManagement.showCreateModal,
    fetchPermissionGroups,
  ]);

  useEffect(() => {
    if (
      policyManagement.showPolicyModal
      && String(policyManagement.policyForm.user_type || 'normal') === 'sub_admin'
    ) {
      fetchPermissionGroups();
    }
  }, [
    fetchPermissionGroups,
    policyManagement.policyForm.user_type,
    policyManagement.showPolicyModal,
  ]);

  const statusManagement = useUserStatusManagement({
    fetchUsers,
    mapErrorMessage: mapUserManagementErrorMessage,
    onError: setError,
  });

  const deletion = useUserDeletion({
    fetchUsers,
    mapErrorMessage: mapUserManagementErrorMessage,
    onError: setError,
  });

  return buildUserManagementState({
    capabilities,
    dataState: {
      allUsers,
      loading,
      error,
      canManageUsers,
      availableGroups,
      permissionGroupsLoading,
      permissionGroupsError,
      companies,
      departments,
      orgDirectoryError,
      fetchPermissionGroups,
    },
    createManagement,
    policyManagement,
    knowledgeDirectoryState: {
      kbDirectoryNodes,
      kbDirectoryLoading,
      kbDirectoryError,
      kbDirectoryCreatingRoot,
      kbDirectoryCreateError,
      managedKbRootInvalid,
      handleCreateModalRootDirectory,
      handlePolicyRootDirectory,
    },
    viewModel: {
      filters,
      setFilters,
      filteredUsers,
      groupedUsers,
      subAdminOptions,
      policySubAdminOptions,
      handleResetFilters,
    },
    actions,
    passwordReset,
    groupAssignment,
    statusManagement,
    deletion,
  });
};
