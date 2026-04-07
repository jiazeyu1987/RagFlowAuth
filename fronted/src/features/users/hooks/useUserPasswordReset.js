import { useCallback, useState } from 'react';
import { usersApi } from '../api';
import { canResetManagedUserPassword } from '../utils/userManagementRules';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { prepareResetPasswordSubmission } from '../utils/userManagementSubmissions';
import {
  buildClosedResetPasswordState,
  buildOpenedResetPasswordState,
} from '../utils/userManagementModalState';
import {
  RESET_PASSWORD_ERROR,
  getResetPasswordValidationMessage,
} from '../utils/userManagementMessages';
import {
  bindStateAction,
  runStateAction,
} from '../utils/userManagementActionRunners';

export const useUserPasswordReset = ({
  actorRole,
  actorUserId,
  mapErrorMessage,
}) => {
  const [showResetPasswordModal, setShowResetPasswordModal] = useState(false);
  const [resetPasswordUser, setResetPasswordUser] = useState(null);
  const [resetPasswordValue, setResetPasswordValue] = useState('');
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState('');
  const [resetPasswordSubmitting, setResetPasswordSubmitting] = useState(false);
  const [resetPasswordError, setResetPasswordError] = useState(null);

  const applyResetPasswordState = useCallback((nextState) => {
    setShowResetPasswordModal(nextState.showResetPasswordModal);
    setResetPasswordUser(nextState.resetPasswordUser);
    setResetPasswordValue(nextState.resetPasswordValue);
    setResetPasswordConfirm(nextState.resetPasswordConfirm);
    setResetPasswordError(nextState.resetPasswordError);
  }, []);

  const canResetPasswordForUser = useCallback(
    (targetUser) =>
      canResetManagedUserPassword({
        actorRole,
        actorUserId,
        targetUser,
      }),
    [actorRole, actorUserId]
  );

  const handleOpenResetPassword = useCallback(
    (targetUser) => {
      if (!canResetPasswordForUser(targetUser)) return;
      runStateAction(
        applyResetPasswordState,
        buildOpenedResetPasswordState,
        targetUser
      );
    },
    [applyResetPasswordState, canResetPasswordForUser]
  );

  const handleCloseResetPassword = useCallback(
    bindStateAction(
      applyResetPasswordState,
      buildClosedResetPasswordState
    ),
    [applyResetPasswordState]
  );

  const handleSubmitResetPassword = useCallback(async () => {
    setResetPasswordError(null);
    await runPreparedUserManagementMutation({
      prepareSubmission: () =>
        prepareResetPasswordSubmission({
          resetPasswordUser,
          resetPasswordValue,
          resetPasswordConfirm,
        }),
      mapErrorMessage,
      fallbackMessage: RESET_PASSWORD_ERROR,
      setError: setResetPasswordError,
      getBlockingMessage: (preparedSubmission) =>
        getResetPasswordValidationMessage(preparedSubmission.errorCode),
      execute: (submission) => usersApi.resetPassword(submission.userId, submission.password),
      onSuccess: () => handleCloseResetPassword(),
      setPending: setResetPasswordSubmitting,
    });
  }, [
    handleCloseResetPassword,
    mapErrorMessage,
    resetPasswordConfirm,
    resetPasswordUser,
    resetPasswordValue,
  ]);

  return {
    showResetPasswordModal,
    resetPasswordUser,
    resetPasswordValue,
    resetPasswordConfirm,
    resetPasswordSubmitting,
    resetPasswordError,
    canResetPasswordForUser,
    setResetPasswordValue,
    setResetPasswordConfirm,
    handleOpenResetPassword,
    handleCloseResetPassword,
    handleSubmitResetPassword,
  };
};
