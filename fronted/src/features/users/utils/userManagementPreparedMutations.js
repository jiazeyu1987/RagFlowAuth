import { resolvePreparedUserManagementSubmission } from './userManagementSubmissionFlow';
import { runUserManagementMutation } from './userManagementMutations';

export const runPreparedUserManagementMutation = async ({
  prepareSubmission,
  getBlockingMessage,
  mapErrorMessage,
  fallbackMessage,
  setError,
  onPrepared,
  execute,
  onSuccess,
  onFinally,
  setPending,
}) => {
  const submission = resolvePreparedUserManagementSubmission({
    prepareSubmission,
    getBlockingMessage,
    mapErrorMessage,
    fallbackMessage,
    setError,
  });
  if (submission.skipped) {
    return { ok: false, skipped: true };
  }

  await onPrepared?.(submission);

  const mutation = await runUserManagementMutation({
    execute: () => execute(submission),
    mapErrorMessage,
    fallbackMessage,
    onMappedError: setError,
    onSuccess,
    onFinally,
    setPending,
  });

  return {
    ...mutation,
    submission,
  };
};
