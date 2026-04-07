import { useCallback } from 'react';
import { usersApi } from '../api';
import {
  DELETE_USER_CONFIRM_MESSAGE,
  DELETE_USER_ERROR,
} from '../utils/userManagementMessages';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { prepareDeleteUserSubmission } from '../utils/userManagementSubmissions';

export const useUserDeletion = ({
  fetchUsers,
  mapErrorMessage,
  onError,
}) => {
  const handleDeleteUser = useCallback(
    async (userId) => {
      if (!window.confirm(DELETE_USER_CONFIRM_MESSAGE)) return;
      await runPreparedUserManagementMutation({
        prepareSubmission: () => prepareDeleteUserSubmission({ userId }),
        mapErrorMessage,
        fallbackMessage: DELETE_USER_ERROR,
        setError: onError,
        execute: (submission) => usersApi.remove(submission.userId),
        onSuccess: () => fetchUsers(),
      });
    },
    [fetchUsers, mapErrorMessage, onError]
  );

  return {
    handleDeleteUser,
  };
};
