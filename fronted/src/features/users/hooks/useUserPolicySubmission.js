import { useCallback, useState } from 'react';
import { usersApi } from '../api';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { preparePolicyUpdateSubmission } from '../utils/userManagementSubmissions';
import { SAVE_POLICY_ERROR } from '../utils/userManagementMessages';

export const useUserPolicySubmission = ({
  fetchUsers,
  kbDirectoryNodes,
  orgDirectoryError,
  policyUser,
  policyForm,
  setPolicyError,
  handleClosePolicyModal,
  mapErrorMessage,
}) => {
  const [policySubmitting, setPolicySubmitting] = useState(false);

  const handleSavePolicy = useCallback(async () => {
    setPolicyError(null);
    await runPreparedUserManagementMutation({
      prepareSubmission: () =>
        preparePolicyUpdateSubmission({
          policyUser,
          policyForm,
          kbDirectoryNodes,
          orgDirectoryError,
        }),
      mapErrorMessage,
      fallbackMessage: SAVE_POLICY_ERROR,
      setError: setPolicyError,
      execute: (submission) => usersApi.update(submission.userId, submission.payload),
      onSuccess: async () => {
        handleClosePolicyModal();
        await fetchUsers();
      },
      setPending: setPolicySubmitting,
    });
  }, [
    fetchUsers,
    handleClosePolicyModal,
    kbDirectoryNodes,
    mapErrorMessage,
    orgDirectoryError,
    policyForm,
    policyUser,
    setPolicyError,
  ]);

  return {
    policySubmitting,
    handleSavePolicy,
  };
};
