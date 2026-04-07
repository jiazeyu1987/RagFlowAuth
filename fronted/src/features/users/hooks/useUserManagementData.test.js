import { act, renderHook, waitFor } from '@testing-library/react';
import { permissionGroupsApi } from '../../permissionGroups/api';
import { orgDirectoryApi } from '../../orgDirectory/api';
import { usersApi } from '../api';
import { ORG_NO_DEPARTMENT_MESSAGE } from '../utils/userManagementMessages';
import { useUserManagementData } from './useUserManagementData';

jest.mock('../api', () => ({
  usersApi: {
    list: jest.fn(),
  },
}));

jest.mock('../../permissionGroups/api', () => ({
  permissionGroupsApi: {
    listAssignable: jest.fn(),
  },
}));

jest.mock('../../orgDirectory/api', () => ({
  orgDirectoryApi: {
    listCompanies: jest.fn(),
    listDepartments: jest.fn(),
  },
}));

describe('useUserManagementData', () => {
  const originalConsoleError = console.error;

  beforeEach(() => {
    jest.clearAllMocks();
    usersApi.list.mockResolvedValue([]);
    permissionGroupsApi.listAssignable.mockResolvedValue([]);
    orgDirectoryApi.listCompanies.mockResolvedValue([{ company_id: 1, company_name: 'A Corp' }]);
    orgDirectoryApi.listDepartments.mockResolvedValue([{ department_id: 11, department_name: 'R&D' }]);
    console.error = jest.fn();
  });

  afterEach(() => {
    console.error = originalConsoleError;
  });

  it('loads users and org directory on mount without eagerly loading permission groups', async () => {
    const can = jest.fn((resource, action) => resource === 'users' && action === 'manage');
    usersApi.list.mockResolvedValue([{ user_id: 'u-1', username: 'alice' }]);

    const { result } = renderHook(() =>
      useUserManagementData({
        can,
        isAdminUser: true,
        isSubAdminUser: false,
      })
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(can).toHaveBeenCalledWith('users', 'manage');
    expect(usersApi.list).toHaveBeenCalledTimes(1);
    expect(permissionGroupsApi.listAssignable).not.toHaveBeenCalled();
    expect(orgDirectoryApi.listCompanies).toHaveBeenCalledTimes(1);
    expect(orgDirectoryApi.listDepartments).toHaveBeenCalledTimes(1);
    expect(result.current.canManageUsers).toBe(true);
    expect(result.current.allUsers).toEqual([{ user_id: 'u-1', username: 'alice' }]);
    expect(result.current.availableGroups).toEqual([]);
    expect(result.current.permissionGroupsLoading).toBe(false);
    expect(result.current.permissionGroupsError).toBeNull();
    expect(result.current.companies).toEqual([{ company_id: 1, company_name: 'A Corp' }]);
    expect(result.current.departments).toEqual([{ department_id: 11, department_name: 'R&D' }]);
    expect(result.current.orgDirectoryError).toBeNull();
  });

  it('loads assignable permission groups only when requested and caches the first result', async () => {
    permissionGroupsApi.listAssignable.mockResolvedValue([{ group_id: 7, name: 'Operators' }]);

    const { result } = renderHook(() =>
      useUserManagementData({
        can: () => true,
        isAdminUser: true,
        isSubAdminUser: false,
      })
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.fetchPermissionGroups();
      await result.current.fetchPermissionGroups();
    });

    expect(permissionGroupsApi.listAssignable).toHaveBeenCalledTimes(1);
    expect(result.current.availableGroups).toEqual([{ group_id: 7, name: 'Operators' }]);
    expect(result.current.permissionGroupsError).toBeNull();
  });

  it('fails fast with the fixed org-directory message when departments are missing', async () => {
    orgDirectoryApi.listDepartments.mockResolvedValueOnce([]);

    const { result } = renderHook(() =>
      useUserManagementData({
        can: () => true,
        isAdminUser: true,
        isSubAdminUser: false,
      })
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(result.current.orgDirectoryError).toBe(ORG_NO_DEPARTMENT_MESSAGE));
  });

  it('skips assignable-group loading for non-admin viewers even when asked explicitly', async () => {
    const { result } = renderHook(() =>
      useUserManagementData({
        can: () => false,
        isAdminUser: false,
        isSubAdminUser: false,
      })
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.fetchPermissionGroups();
    });

    expect(permissionGroupsApi.listAssignable).not.toHaveBeenCalled();
    expect(result.current.availableGroups).toEqual([]);
    expect(result.current.canManageUsers).toBe(false);
  });

  it('skips org-directory loading for sub-admin actors and loads groups on demand', async () => {
    permissionGroupsApi.listAssignable.mockResolvedValue([{ group_id: 7, group_name: 'G7' }]);

    const { result } = renderHook(() =>
      useUserManagementData({
        can: () => true,
        isAdminUser: false,
        isSubAdminUser: true,
      })
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(usersApi.list).toHaveBeenCalledTimes(1);
    expect(permissionGroupsApi.listAssignable).not.toHaveBeenCalled();
    expect(orgDirectoryApi.listCompanies).not.toHaveBeenCalled();
    expect(orgDirectoryApi.listDepartments).not.toHaveBeenCalled();
    expect(result.current.companies).toEqual([]);
    expect(result.current.departments).toEqual([]);
    expect(result.current.orgDirectoryError).toBeNull();

    await act(async () => {
      await result.current.fetchPermissionGroups();
    });

    expect(permissionGroupsApi.listAssignable).toHaveBeenCalledTimes(1);
    expect(result.current.availableGroups).toEqual([{ group_id: 7, group_name: 'G7' }]);
  });

  it('stores a permission-group load error and logs it when the request fails', async () => {
    permissionGroupsApi.listAssignable.mockRejectedValueOnce(new Error('permission_groups_unavailable'));

    const { result } = renderHook(() =>
      useUserManagementData({
        can: () => true,
        isAdminUser: true,
        isSubAdminUser: false,
      })
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.fetchPermissionGroups();
    });

    expect(result.current.availableGroups).toEqual([]);
    expect(result.current.permissionGroupsError).toBe('permission_groups_unavailable');
    expect(console.error).toHaveBeenCalledWith(
      'Failed to load permission groups:',
      'permission_groups_unavailable'
    );
  });
});
