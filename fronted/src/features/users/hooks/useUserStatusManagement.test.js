import { act, renderHook, waitFor } from '@testing-library/react';
import { usersApi } from '../api';
import { useUserStatusManagement } from './useUserStatusManagement';

jest.mock('../api', () => ({
  usersApi: {
    update: jest.fn(),
  },
}));

describe('useUserStatusManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    usersApi.update.mockResolvedValue({});
  });

  it('opens the disable modal for active users and validates scheduled disable input', async () => {
    const { result } = renderHook(() =>
      useUserStatusManagement({
        fetchUsers: jest.fn(),
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.handleToggleUserStatus({
        user_id: 'u-1',
        username: 'alice',
        role: 'viewer',
        status: 'active',
        disable_login_enabled: false,
        disable_login_until_ms: null,
      });
    });

    expect(result.current.showDisableUserModal).toBe(true);

    act(() => {
      result.current.handleChangeDisableMode('until');
    });

    await act(async () => {
      await result.current.handleConfirmDisableUser();
    });

    expect(result.current.disableUserError).toBe('请选择禁用到期日期');
    expect(usersApi.update).not.toHaveBeenCalled();
  });

  it('reenables disabled users through the normalized payload', async () => {
    const fetchUsers = jest.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useUserStatusManagement({
        fetchUsers,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleToggleUserStatus({
        user_id: 'u-disabled',
        username: 'alice',
        role: 'viewer',
        status: 'active',
        disable_login_enabled: true,
        disable_login_until_ms: 4102444799000,
      });
    });

    await waitFor(() =>
      expect(usersApi.update).toHaveBeenCalledWith('u-disabled', {
        status: 'active',
        disable_login_enabled: false,
        disable_login_until_ms: null,
      })
    );
    expect(fetchUsers).toHaveBeenCalledTimes(1);
  });
});
