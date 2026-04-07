import { runPreparedUserManagementMutation } from './userManagementPreparedMutations';

describe('userManagementPreparedMutations', () => {
  it('runs the prepared submission through the mutation executor', async () => {
    const execute = jest.fn().mockResolvedValue({ ok: true });
    const onSuccess = jest.fn().mockResolvedValue(undefined);
    const onPrepared = jest.fn().mockResolvedValue(undefined);
    const setError = jest.fn();

    await expect(
      runPreparedUserManagementMutation({
        prepareSubmission: () => ({ userId: 'u-1', payload: { role: 'viewer' } }),
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        setError,
        onPrepared,
        execute,
        onSuccess,
      })
    ).resolves.toEqual({
      ok: true,
      result: { ok: true },
      submission: { userId: 'u-1', payload: { role: 'viewer' } },
    });

    expect(onPrepared).toHaveBeenCalledWith({ userId: 'u-1', payload: { role: 'viewer' } });
    expect(execute).toHaveBeenCalledWith({ userId: 'u-1', payload: { role: 'viewer' } });
    expect(onSuccess).toHaveBeenCalledWith({ ok: true });
    expect(setError).not.toHaveBeenCalled();
  });

  it('stops before the mutation when submission preparation is skipped or blocked', async () => {
    const execute = jest.fn();
    const setError = jest.fn();

    await expect(
      runPreparedUserManagementMutation({
        prepareSubmission: () => ({ skipped: true }),
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        setError,
        execute,
      })
    ).resolves.toEqual({ ok: false, skipped: true });

    await expect(
      runPreparedUserManagementMutation({
        prepareSubmission: () => ({ validationMessage: 'need_manager' }),
        getBlockingMessage: (submission) => submission.validationMessage,
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        setError,
        execute,
      })
    ).resolves.toEqual({ ok: false, skipped: true });

    expect(execute).not.toHaveBeenCalled();
    expect(setError).toHaveBeenCalledWith('need_manager');
  });
});
