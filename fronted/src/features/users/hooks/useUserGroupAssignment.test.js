import { act, renderHook, waitFor } from '@testing-library/react';
import { usersApi } from '../api';
import { useUserGroupAssignment } from './useUserGroupAssignment';

jest.mock('../api', () => ({
  usersApi: {
    update: jest.fn(),
  },
}));

describe('useUserGroupAssignment', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    usersApi.update.mockResolvedValue({});
  });

  it('opens only for manageable users and drops stale group ids after groups are loaded', async () => {
    const ensureAvailableGroupsLoaded = jest.fn().mockResolvedValue({
      ok: true,
      result: [{ group_id: 7 }, { group_id: 9 }],
    });

    const { result } = renderHook(() =>
      useUserGroupAssignment({
        actorRole: 'sub_admin',
        actorUserId: 'sub-1',
        availableGroups: [],
        ensureAvailableGroupsLoaded,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleAssignGroup({
        user_id: 'u-other',
        role: 'viewer',
        manager_user_id: 'someone-else',
        group_ids: [7],
      });
    });
    expect(ensureAvailableGroupsLoaded).not.toHaveBeenCalled();
    expect(result.current.showGroupModal).toBe(false);

    await act(async () => {
      await result.current.handleAssignGroup({
        user_id: 'u-owned',
        role: 'viewer',
        manager_user_id: 'sub-1',
        group_ids: [11, 7, 9, 9],
      });
    });

    expect(ensureAvailableGroupsLoaded).toHaveBeenCalledTimes(1);
    expect(result.current.showGroupModal).toBe(true);
    expect(result.current.selectedGroupIds).toEqual([7, 9]);
  });

  it('does not open the modal when permission groups fail to load', async () => {
    const ensureAvailableGroupsLoaded = jest.fn().mockResolvedValue({
      ok: false,
      errorMessage: 'permission_groups_unavailable',
    });

    const { result } = renderHook(() =>
      useUserGroupAssignment({
        actorRole: 'admin',
        actorUserId: 'admin-1',
        availableGroups: [],
        ensureAvailableGroupsLoaded,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleAssignGroup({
        user_id: 'u-1',
        role: 'viewer',
        manager_user_id: 'sub-1',
        group_ids: [7],
      });
    });

    expect(result.current.showGroupModal).toBe(false);
  });

  it('saves group assignments through the user api and closes the modal', async () => {
    const onSaved = jest.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useUserGroupAssignment({
        actorRole: 'admin',
        actorUserId: 'admin-1',
        availableGroups: [{ group_id: 7 }],
        ensureAvailableGroupsLoaded: jest.fn().mockResolvedValue({
          ok: true,
          result: [{ group_id: 7 }],
        }),
        mapErrorMessage: (value) => value,
        onSaved,
      })
    );

    await act(async () => {
      await result.current.handleAssignGroup({
        user_id: 'u-1',
        role: 'viewer',
        manager_user_id: 'sub-1',
        group_ids: [7],
      });
    });

    await act(async () => {
      await result.current.handleSaveGroup();
    });

    await waitFor(() => expect(usersApi.update).toHaveBeenCalledWith('u-1', { group_ids: [7] }));
    expect(onSaved).toHaveBeenCalledTimes(1);
    expect(result.current.showGroupModal).toBe(false);
  });
});
