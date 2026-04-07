import { resolvePreparedUserManagementSubmission } from './userManagementSubmissionFlow';

describe('userManagementSubmissionFlow', () => {
  it('returns the prepared submission when there are no blocking conditions', () => {
    const setError = jest.fn();

    expect(
      resolvePreparedUserManagementSubmission({
        prepareSubmission: () => ({ userId: 'u-1', payload: { role: 'viewer' } }),
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        setError,
      })
    ).toEqual({
      userId: 'u-1',
      payload: { role: 'viewer' },
    });
    expect(setError).not.toHaveBeenCalled();
  });

  it('stops on skipped or blocking submissions without throwing', () => {
    const setError = jest.fn();

    expect(
      resolvePreparedUserManagementSubmission({
        prepareSubmission: () => ({ skipped: true }),
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        setError,
      })
    ).toEqual({ skipped: true });

    expect(
      resolvePreparedUserManagementSubmission({
        prepareSubmission: () => ({ errorMessage: 'org_error' }),
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        setError,
      })
    ).toEqual({ skipped: true });

    expect(setError).toHaveBeenCalledWith('org_error');
  });

  it('maps thrown preparation errors and supports custom blocking-message selectors', () => {
    const setError = jest.fn();

    expect(
      resolvePreparedUserManagementSubmission({
        prepareSubmission: () => {
          throw new Error('users_prepare_failed');
        },
        mapErrorMessage: (value) => `mapped:${value}`,
        fallbackMessage: 'fallback_error',
        setError,
      })
    ).toEqual({ skipped: true });

    expect(
      resolvePreparedUserManagementSubmission({
        prepareSubmission: () => ({ validationMessage: 'need_manager' }),
        mapErrorMessage: (value) => value,
        fallbackMessage: 'fallback_error',
        setError,
        getBlockingMessage: (submission) => submission.validationMessage,
      })
    ).toEqual({ skipped: true });

    expect(setError).toHaveBeenNthCalledWith(1, 'mapped:users_prepare_failed');
    expect(setError).toHaveBeenNthCalledWith(2, 'need_manager');
  });
});
