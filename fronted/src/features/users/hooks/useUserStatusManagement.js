import { useCallback, useState } from 'react';
import { usersApi } from '../api';
import { resolveUserStatusToggleAction } from '../utils/userManagementDerivedState';
import {
  buildClosedDisableUserState,
  buildOpenedDisableUserState,
} from '../utils/userManagementModalState';
import {
  prepareDisableUserSubmission,
  prepareEnableUserSubmission,
} from '../utils/userManagementSubmissions';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import {
  DISABLE_USER_ERROR,
  TOGGLE_USER_STATUS_ERROR,
} from '../utils/userManagementMessages';
import { runStateAction } from '../utils/userManagementActionRunners';

export const useUserStatusManagement = ({
  fetchUsers,
  mapErrorMessage,
  onError,
}) => {
  const [statusUpdatingUserId, setStatusUpdatingUserId] = useState(null);
  const [showDisableUserModal, setShowDisableUserModal] = useState(false);
  const [disableTargetUser, setDisableTargetUser] = useState(null);
  const [disableMode, setDisableMode] = useState('immediate');
  const [disableUntilDate, setDisableUntilDate] = useState('');
  const [disableUserError, setDisableUserError] = useState(null);

  const applyDisableUserState = useCallback((nextState) => {
    setShowDisableUserModal(nextState.showDisableUserModal);
    setDisableTargetUser(nextState.disableTargetUser);
    setDisableMode(nextState.disableMode);
    setDisableUntilDate(nextState.disableUntilDate);
    setDisableUserError(nextState.disableUserError);
  }, []);

  const handleCloseDisableUserModal = useCallback(() => {
    runStateAction(
      applyDisableUserState,
      buildClosedDisableUserState
    );
  }, [applyDisableUserState]);

  const handleChangeDisableMode = useCallback((mode) => {
    const nextMode = mode === 'until' ? 'until' : 'immediate';
    setDisableMode(nextMode);
    if (nextMode !== 'until') {
      setDisableUntilDate('');
    }
    setDisableUserError(null);
  }, []);

  const handleChangeDisableUntilDate = useCallback((value) => {
    setDisableUntilDate(String(value || ''));
    setDisableUserError(null);
  }, []);

  const handleConfirmDisableUser = useCallback(async () => {
    setDisableUserError(null);

    const mutation = await runPreparedUserManagementMutation({
      prepareSubmission: () =>
        prepareDisableUserSubmission({
          disableTargetUser,
          disableMode,
          disableUntilDate,
        }),
      mapErrorMessage,
      fallbackMessage: DISABLE_USER_ERROR,
      setError: setDisableUserError,
      onPrepared: (submission) => setStatusUpdatingUserId(submission.userId),
      execute: (submission) => usersApi.update(submission.userId, submission.payload),
      onSuccess: async () => {
        handleCloseDisableUserModal();
        await fetchUsers();
      },
      onFinally: () => setStatusUpdatingUserId(null),
    });
    if (mutation.skipped) {
      return;
    }
  }, [
    disableMode,
    disableTargetUser,
    disableUntilDate,
    fetchUsers,
    handleCloseDisableUserModal,
    mapErrorMessage,
  ]);

  const handleToggleUserStatus = useCallback(
    async (targetUser) => {
      const action = resolveUserStatusToggleAction(targetUser);
      if (action.type === 'ignore') return;
      if (action.type === 'disable') {
        runStateAction(
          applyDisableUserState,
          buildOpenedDisableUserState,
          targetUser
        );
        return;
      }

      await runPreparedUserManagementMutation({
        prepareSubmission: () => prepareEnableUserSubmission({ targetUser }),
        mapErrorMessage,
        fallbackMessage: TOGGLE_USER_STATUS_ERROR,
        setError: onError,
        onPrepared: (submission) => setStatusUpdatingUserId(submission.userId),
        execute: (submission) => usersApi.update(submission.userId, submission.payload),
        onSuccess: () => fetchUsers(),
        onFinally: () => setStatusUpdatingUserId(null),
      });
    },
    [applyDisableUserState, fetchUsers, mapErrorMessage, onError]
  );

  return {
    statusUpdatingUserId,
    showDisableUserModal,
    disableTargetUser,
    disableMode,
    disableUntilDate,
    disableUserError,
    handleCloseDisableUserModal,
    handleChangeDisableMode,
    handleChangeDisableUntilDate,
    handleConfirmDisableUser,
    handleToggleUserStatus,
  };
};
