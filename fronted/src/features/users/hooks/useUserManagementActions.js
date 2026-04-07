import { useCallback, useMemo } from 'react';
import { useUserPolicySubmission } from './useUserPolicySubmission';
import {
  bindKbDirectoryErrorClearedActions,
} from '../utils/userManagementActionRunners';

export const useUserManagementActions = ({
  createManagement,
  policyManagement,
  kbDirectoryNodes,
  orgDirectoryError,
  clearKbDirectoryCreateError,
  fetchUsers,
  mapErrorMessage,
}) => {
  const clearedActions = useMemo(
    () =>
      bindKbDirectoryErrorClearedActions(clearKbDirectoryCreateError, {
        handleOpenCreateModal: createManagement.handleOpenCreateModal,
        handleCloseCreateModal: createManagement.handleCloseCreateModal,
        setNewUserField: createManagement.setNewUserField,
        handleOpenPolicyModal: policyManagement.handleOpenPolicyModal,
        handleClosePolicyModal: policyManagement.handleClosePolicyModal,
        handleChangePolicyForm: policyManagement.handleChangePolicyForm,
      }),
    [
      clearKbDirectoryCreateError,
      createManagement.handleCloseCreateModal,
      createManagement.handleOpenCreateModal,
      createManagement.setNewUserField,
      policyManagement.handleChangePolicyForm,
      policyManagement.handleClosePolicyModal,
      policyManagement.handleOpenPolicyModal,
    ]
  );

  const handleCreateUser = useCallback(
    (event) =>
      createManagement.handleCreateUser(event, {
        kbDirectoryNodes,
        orgDirectoryError,
      }),
    [createManagement, kbDirectoryNodes, orgDirectoryError]
  );

  const {
    handleOpenCreateModal,
    handleCloseCreateModal,
    setNewUserField,
    handleOpenPolicyModal,
    handleClosePolicyModal,
    handleChangePolicyForm,
  } = clearedActions;

  const policySubmission = useUserPolicySubmission({
    fetchUsers,
    kbDirectoryNodes,
    orgDirectoryError,
    policyUser: policyManagement.policyUser,
    policyForm: policyManagement.policyForm,
    setPolicyError: policyManagement.setPolicyError,
    handleClosePolicyModal,
    mapErrorMessage,
  });

  return {
    policySubmitting: policySubmission.policySubmitting,
    handleOpenCreateModal,
    handleCloseCreateModal,
    setNewUserField,
    handleCreateUser,
    handleOpenPolicyModal,
    handleClosePolicyModal,
    handleChangePolicyForm,
    handleSavePolicy: policySubmission.handleSavePolicy,
  };
};
