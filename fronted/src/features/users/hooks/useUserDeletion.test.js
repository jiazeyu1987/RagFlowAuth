import { act, renderHook, waitFor } from '@testing-library/react';
import { usersApi } from '../api';
import { useUserDeletion } from './useUserDeletion';

jest.mock('../api', () => ({
  usersApi: {
    remove: jest.fn(),
  },
}));

describe('useUserDeletion', () => {
  const originalConfirm = window.confirm;

  beforeEach(() => {
    jest.clearAllMocks();
    usersApi.remove.mockResolvedValue({});
  });

  afterEach(() => {
    window.confirm = originalConfirm;
  });

  it('deletes after confirmation and reloads users', async () => {
    const fetchUsers = jest.fn().mockResolvedValue(undefined);
    window.confirm = jest.fn(() => true);

    const { result } = renderHook(() =>
      useUserDeletion({
        fetchUsers,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleDeleteUser('u-1');
    });

    await waitFor(() => expect(usersApi.remove).toHaveBeenCalledWith('u-1'));
    expect(fetchUsers).toHaveBeenCalledTimes(1);
  });

  it('stops immediately when the user cancels the confirmation dialog', async () => {
    window.confirm = jest.fn(() => false);
    const fetchUsers = jest.fn();

    const { result } = renderHook(() =>
      useUserDeletion({
        fetchUsers,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleDeleteUser('u-1');
    });

    expect(usersApi.remove).not.toHaveBeenCalled();
    expect(fetchUsers).not.toHaveBeenCalled();
  });

  it('skips deletion when the prepared submission has no target user id', async () => {
    window.confirm = jest.fn(() => true);
    const fetchUsers = jest.fn();

    const { result } = renderHook(() =>
      useUserDeletion({
        fetchUsers,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleDeleteUser('');
    });

    expect(usersApi.remove).not.toHaveBeenCalled();
    expect(fetchUsers).not.toHaveBeenCalled();
  });
});
