import { runUserManagementMutation } from './userManagementMutations';

describe('userManagementMutations', () => {
  it('runs success callbacks and clears pending state after a successful mutation', async () => {
    const execute = jest.fn().mockResolvedValue({ id: 'node-1' });
    const onSuccess = jest.fn().mockResolvedValue(undefined);
    const setPending = jest.fn();
    const onFinally = jest.fn();

    await expect(
      runUserManagementMutation({
        execute,
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        onSuccess,
        onFinally,
        setPending,
      })
    ).resolves.toEqual({ ok: true, result: { id: 'node-1' } });

    expect(execute).toHaveBeenCalledTimes(1);
    expect(onSuccess).toHaveBeenCalledWith({ id: 'node-1' });
    expect(setPending).toHaveBeenNthCalledWith(1, true);
    expect(setPending).toHaveBeenNthCalledWith(2, false);
    expect(onFinally).toHaveBeenCalledTimes(1);
  });

  it('maps errors, reports them, and still clears pending state on failure', async () => {
    const execute = jest.fn().mockRejectedValue(new Error('users_update_failed'));
    const onMappedError = jest.fn();
    const setPending = jest.fn();
    const onFinally = jest.fn();

    await expect(
      runUserManagementMutation({
        execute,
        mapErrorMessage: (value) => `mapped:${value}`,
        fallbackMessage: 'fallback_error',
        onMappedError,
        onFinally,
        setPending,
      })
    ).resolves.toEqual({
      ok: false,
      errorMessage: 'mapped:users_update_failed',
    });

    expect(onMappedError).toHaveBeenCalledWith('mapped:users_update_failed');
    expect(setPending).toHaveBeenNthCalledWith(1, true);
    expect(setPending).toHaveBeenNthCalledWith(2, false);
    expect(onFinally).toHaveBeenCalledTimes(1);
  });

  it('falls back to the provided default message when the error has no message', async () => {
    const onMappedError = jest.fn();

    await expect(
      runUserManagementMutation({
        execute: jest.fn().mockRejectedValue({}),
        mapErrorMessage: (value) => `mapped:${value}`,
        fallbackMessage: 'fallback_error',
        onMappedError,
      })
    ).resolves.toEqual({
      ok: false,
      errorMessage: 'mapped:fallback_error',
    });

    expect(onMappedError).toHaveBeenCalledWith('mapped:fallback_error');
  });
});
