import { act, renderHook, waitFor } from '@testing-library/react';
import { usersApi } from '../api';
import { useUserPasswordReset } from './useUserPasswordReset';

jest.mock('../api', () => ({
  usersApi: {
    resetPassword: jest.fn(),
  },
}));

describe('useUserPasswordReset', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    usersApi.resetPassword.mockResolvedValue({});
  });

  it('allows sub admins to open reset only for themselves or owned viewers', () => {
    const { result } = renderHook(() =>
      useUserPasswordReset({
        actorRole: 'sub_admin',
        actorUserId: 'sub-1',
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.handleOpenResetPassword({
        user_id: 'u-other',
        role: 'viewer',
        manager_user_id: 'someone-else',
      });
    });
    expect(result.current.showResetPasswordModal).toBe(false);

    act(() => {
      result.current.handleOpenResetPassword({
        user_id: 'u-owned',
        role: 'viewer',
        manager_user_id: 'sub-1',
      });
    });
    expect(result.current.showResetPasswordModal).toBe(true);
  });

  it('fails fast on mismatched passwords and does not call the api', async () => {
    const { result } = renderHook(() =>
      useUserPasswordReset({
        actorRole: 'admin',
        actorUserId: 'admin-1',
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.handleOpenResetPassword({ user_id: 'u-1', role: 'viewer' });
      result.current.setResetPasswordValue('Secret123');
      result.current.setResetPasswordConfirm('Secret124');
    });

    await act(async () => {
      await result.current.handleSubmitResetPassword();
    });

    expect(result.current.resetPasswordError).toBe('两次输入的新密码不一致');
    expect(usersApi.resetPassword).not.toHaveBeenCalled();
  });

  it('submits the normalized reset payload and closes the modal', async () => {
    const { result } = renderHook(() =>
      useUserPasswordReset({
        actorRole: 'admin',
        actorUserId: 'admin-1',
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.handleOpenResetPassword({ user_id: 'u-1', role: 'viewer' });
      result.current.setResetPasswordValue('Secret123');
      result.current.setResetPasswordConfirm('Secret123');
    });

    await act(async () => {
      await result.current.handleSubmitResetPassword();
    });

    await waitFor(() => expect(usersApi.resetPassword).toHaveBeenCalledWith('u-1', 'Secret123'));
    expect(result.current.showResetPasswordModal).toBe(false);
  });
});
