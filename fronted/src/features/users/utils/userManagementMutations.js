export const runUserManagementMutation = async ({
  execute,
  mapErrorMessage,
  fallbackMessage,
  onMappedError,
  onSuccess,
  onFinally,
  setPending,
}) => {
  try {
    setPending?.(true);
    const result = await execute();
    await onSuccess?.(result);
    return {
      ok: true,
      result,
    };
  } catch (err) {
    const errorMessage = mapErrorMessage(err?.message || fallbackMessage);
    onMappedError?.(errorMessage);
    return {
      ok: false,
      errorMessage,
    };
  } finally {
    setPending?.(false);
    onFinally?.();
  }
};
