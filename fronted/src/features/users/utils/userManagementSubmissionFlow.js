export const resolvePreparedUserManagementSubmission = ({
  prepareSubmission,
  mapErrorMessage,
  fallbackMessage,
  setError,
  getBlockingMessage,
}) => {
  try {
    const submission = prepareSubmission();
    if (submission?.skipped) {
      return { skipped: true };
    }

    const blockingMessage =
      typeof getBlockingMessage === 'function'
        ? getBlockingMessage(submission)
        : submission?.errorMessage;
    if (blockingMessage) {
      setError(blockingMessage);
      return { skipped: true };
    }

    return submission;
  } catch (err) {
    setError(mapErrorMessage(err?.message || fallbackMessage));
    return { skipped: true };
  }
};
