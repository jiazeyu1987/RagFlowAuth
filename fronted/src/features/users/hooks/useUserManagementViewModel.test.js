import { act, renderHook, waitFor } from '@testing-library/react';
import { useUserManagementViewModel } from './useUserManagementViewModel';

describe('useUserManagementViewModel', () => {
  const users = [
    { user_id: 'sub-1', username: 'sub_a', full_name: 'Sub A', role: 'sub_admin', status: 'active', company_id: 1 },
    { user_id: 'sub-2', username: 'sub_b', full_name: 'Sub B', role: 'sub_admin', status: 'active', company_id: 2 },
    {
      user_id: 'viewer-1',
      username: 'viewer_a',
      full_name: 'Viewer A',
      role: 'viewer',
      status: 'active',
      company_id: 1,
      department_name: 'QA',
    },
  ];

  it('builds filtered user lists and company-scoped sub-admin options', async () => {
    const { result } = renderHook(() =>
      useUserManagementViewModel({
        allUsers: users,
        createCompanyId: '1',
        policyCompanyId: '1',
        policyUserId: 'sub-1',
      })
    );

    expect(result.current.subAdminOptions).toHaveLength(1);
    expect(result.current.subAdminOptions[0].value).toBe('sub-1');
    expect(result.current.policySubAdminOptions).toEqual([]);

    act(() => {
      result.current.setFilters((prev) => ({ ...prev, q: 'viewer' }));
    });

    await waitFor(() => expect(result.current.filteredUsers).toHaveLength(1));
    expect(result.current.groupedUsers[0].users).toHaveLength(1);
  });

  it('resets filters back to the default shape', async () => {
    const { result } = renderHook(() =>
      useUserManagementViewModel({
        allUsers: users,
        createCompanyId: '',
        policyCompanyId: '',
        policyUserId: '',
      })
    );

    act(() => {
      result.current.setFilters((prev) => ({ ...prev, q: 'viewer', company_id: '1' }));
    });

    await waitFor(() => expect(result.current.filters.q).toBe('viewer'));

    act(() => {
      result.current.handleResetFilters();
    });

    expect(result.current.filters).toEqual({
      q: '',
      company_id: '',
      department_id: '',
      status: '',
      group_id: '',
      assignment_status: '',
      created_from: '',
      created_to: '',
    });
  });
});
