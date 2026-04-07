import { useCallback, useState } from 'react';
import { usersApi } from '../api';
import { DEFAULT_NEW_USER } from '../utils/constants';
import {
  applyManagedUserFieldChange,
  toggleManagedUserDraftGroup,
} from '../utils/userManagementDrafts';
import {
  buildClosedCreateUserState,
  buildOpenedCreateUserState,
} from '../utils/userManagementFormState';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { prepareCreateUserSubmission } from '../utils/userManagementSubmissions';
import { CREATE_USER_ERROR } from '../utils/userManagementMessages';
import {
  bindFormErrorsClearedDraftAction,
  bindKbDirectoryErrorClearedStateAction,
} from '../utils/userManagementActionRunners';
import { useManagedDepartmentReset } from './useManagedDepartmentReset';

export const useUserCreateManagement = ({
  departments,
  fetchUsers,
  mapErrorMessage,
  clearKbDirectoryCreateError,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState(DEFAULT_NEW_USER);
  const [createUserError, setCreateUserError] = useState(null);

  const applyCreateModalState = useCallback((nextState) => {
    setShowCreateModal(nextState.showCreateModal);
    setNewUser(nextState.newUser);
    setCreateUserError(nextState.createUserError);
  }, []);

  const clearMismatchedDepartment = useCallback(() => {
    setNewUser((prev) => ({ ...prev, department_id: '' }));
  }, []);

  useManagedDepartmentReset({
    companyId: newUser.company_id,
    departmentId: newUser.department_id,
    departments,
    resetDepartment: clearMismatchedDepartment,
  });

  const handleOpenCreateModal = useCallback(
    bindKbDirectoryErrorClearedStateAction(
      clearKbDirectoryCreateError,
      applyCreateModalState,
      () => buildOpenedCreateUserState(newUser)
    ),
    [applyCreateModalState, clearKbDirectoryCreateError, newUser]
  );

  const handleCloseCreateModal = useCallback(
    bindKbDirectoryErrorClearedStateAction(
      clearKbDirectoryCreateError,
      applyCreateModalState,
      buildClosedCreateUserState
    ),
    [applyCreateModalState, clearKbDirectoryCreateError]
  );

  const setNewUserField = useCallback(
    bindFormErrorsClearedDraftAction(
      setCreateUserError,
      clearKbDirectoryCreateError,
      setNewUser,
      applyManagedUserFieldChange
    ),
    [clearKbDirectoryCreateError]
  );

  const toggleNewUserGroup = useCallback((groupId, checked) => {
    setCreateUserError(null);
    setNewUser((prev) => toggleManagedUserDraftGroup(prev, groupId, checked));
  }, []);

  const handleCreateUser = useCallback(
    async (event, { kbDirectoryNodes, orgDirectoryError }) => {
      event?.preventDefault?.();
      setCreateUserError(null);
      await runPreparedUserManagementMutation({
        prepareSubmission: () =>
          prepareCreateUserSubmission({
            draft: newUser,
            kbDirectoryNodes,
            orgDirectoryError,
          }),
        mapErrorMessage,
        fallbackMessage: CREATE_USER_ERROR,
        setError: setCreateUserError,
        execute: (submission) => usersApi.create(submission.payload),
        onSuccess: async () => {
          handleCloseCreateModal();
          await fetchUsers();
        },
      });
    },
    [
      fetchUsers,
      handleCloseCreateModal,
      mapErrorMessage,
      newUser,
    ]
  );

  return {
    showCreateModal,
    newUser,
    createUserError,
    handleOpenCreateModal,
    handleCloseCreateModal,
    setNewUserField,
    toggleNewUserGroup,
    handleCreateUser,
  };
};
