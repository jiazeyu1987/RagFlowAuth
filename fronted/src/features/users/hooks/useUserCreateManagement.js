import { useCallback, useEffect, useState } from 'react';
import { usersApi } from '../api';
import { DEFAULT_NEW_USER } from '../utils/constants';
import {
  applyManagedUserFieldChange,
  toggleManagedUserDraftGroup,
  toggleManagedUserDraftTool,
} from '../utils/userManagementDrafts';
import {
  buildClosedCreateUserState,
  buildOpenedCreateUserState,
} from '../utils/userManagementFormState';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { prepareCreateUserSubmission } from '../utils/userManagementSubmissions';
import { CREATE_USER_ERROR } from '../utils/userManagementMessages';
import {
  runStateAction,
} from '../utils/userManagementActionRunners';
import { useManagedDepartmentReset } from './useManagedDepartmentReset';

const DEFAULT_CREATE_COMPANY_NAME = '\u745b\u6cf0\u533b\u7597';

export const useUserCreateManagement = ({
  companies = [],
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

  const resolveDefaultCompanyId = useCallback(() => {
    const targetCompany = (companies || []).find(
      (item) => String(item?.name || '').trim() === DEFAULT_CREATE_COMPANY_NAME
    );
    if (!targetCompany || targetCompany.id == null) {
      return '';
    }
    return String(targetCompany.id);
  }, [companies]);

  useEffect(() => {
    if (!showCreateModal) {
      return;
    }
    const currentCompanyId = String(newUser.company_id || '').trim();
    if (currentCompanyId) {
      return;
    }
    const defaultCompanyId = resolveDefaultCompanyId();
    if (!defaultCompanyId) {
      return;
    }
    setNewUser((previous) => {
      const existingCompanyId = String(previous.company_id || '').trim();
      if (existingCompanyId) {
        return previous;
      }
      return {
        ...previous,
        company_id: defaultCompanyId,
        department_id: '',
      };
    });
  }, [newUser.company_id, resolveDefaultCompanyId, showCreateModal]);

  const handleOpenCreateModal = useCallback(
    () => {
      clearKbDirectoryCreateError?.();
      runStateAction(
        applyCreateModalState,
        () => buildOpenedCreateUserState(newUser)
      );
    },
    [applyCreateModalState, clearKbDirectoryCreateError, newUser]
  );

  const handleCloseCreateModal = useCallback(
    () => {
      clearKbDirectoryCreateError?.();
      runStateAction(
        applyCreateModalState,
        buildClosedCreateUserState
      );
    },
    [applyCreateModalState, clearKbDirectoryCreateError]
  );

  const setNewUserField = useCallback((...args) => {
    setCreateUserError(null);
    clearKbDirectoryCreateError?.();
    setNewUser((previousState) => applyManagedUserFieldChange(previousState, ...args));
  }, [clearKbDirectoryCreateError]);

  const toggleNewUserGroup = useCallback((groupId, checked) => {
    setCreateUserError(null);
    setNewUser((prev) => toggleManagedUserDraftGroup(prev, groupId, checked));
  }, []);

  const toggleNewUserTool = useCallback((toolId, checked) => {
    setCreateUserError(null);
    setNewUser((prev) => toggleManagedUserDraftTool(prev, toolId, checked));
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
    toggleNewUserTool,
    handleCreateUser,
  };
};
