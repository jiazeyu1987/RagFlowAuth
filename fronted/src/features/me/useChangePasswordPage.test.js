import { act, renderHook } from '@testing-library/react';
import meApi from './api';
import useChangePasswordPage from './useChangePasswordPage';
import { useAuth } from '../../hooks/useAuth';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    changePassword: jest.fn(),
  },
}));

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('useChangePasswordPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: {
        username: 'alice',
        full_name: 'Alice',
      },
    });
    meApi.changePassword.mockResolvedValue({ message: 'password_changed' });
  });

  it('submits valid password changes through the me feature api and resets form state', async () => {
    const { result } = renderHook(() => useChangePasswordPage());

    act(() => {
      result.current.setOldPassword('OldPass123');
      result.current.setNewPassword('NewPass123');
      result.current.setConfirmPassword('NewPass123');
    });

    await act(async () => {
      await result.current.handleSubmit({ preventDefault() {} });
    });

    expect(meApi.changePassword).toHaveBeenCalledWith('OldPass123', 'NewPass123');
    expect(result.current.message).toBe('密码修改成功');
    expect(result.current.oldPassword).toBe('');
    expect(result.current.newPassword).toBe('');
    expect(result.current.confirmPassword).toBe('');
  });

  it('blocks weak passwords before calling the api', async () => {
    const { result } = renderHook(() => useChangePasswordPage());

    act(() => {
      result.current.setOldPassword('OldPass123');
      result.current.setNewPassword('password');
      result.current.setConfirmPassword('password');
    });

    await act(async () => {
      await result.current.handleSubmit({ preventDefault() {} });
    });

    expect(meApi.changePassword).not.toHaveBeenCalled();
    expect(result.current.error).toBe('新密码不符合安全策略，请根据红色提示调整');
    expect(result.current.passwordPolicyChecks.find((item) => item.key === 'not-common')?.passed).toBe(false);
  });

  it('maps backend password error codes to user-facing messages', async () => {
    meApi.changePassword.mockRejectedValue(new Error('old_password_incorrect'));

    const { result } = renderHook(() => useChangePasswordPage());

    act(() => {
      result.current.setOldPassword('OldPass123');
      result.current.setNewPassword('NewPass123');
      result.current.setConfirmPassword('NewPass123');
    });

    await act(async () => {
      await result.current.handleSubmit({ preventDefault() {} });
    });

    expect(result.current.error).toBe('旧密码错误');
  });
});
