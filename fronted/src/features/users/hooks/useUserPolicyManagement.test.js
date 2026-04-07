import { act, renderHook, waitFor } from '@testing-library/react';
import { useUserPolicyManagement } from './useUserPolicyManagement';

describe('useUserPolicyManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('opens with a normalized form and clears mismatched departments', async () => {
    const { result } = renderHook(() =>
      useUserPolicyManagement({
        departments: [{ id: 11, company_id: 2, name: 'Ops' }],
      })
    );

    act(() => {
      result.current.handleOpenPolicyModal({
        user_id: 'u-1',
        role: 'viewer',
        full_name: 'Alice',
        company_id: 1,
        department_id: 11,
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: '',
        group_ids: [7],
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
        can_change_password: true,
        status: 'active',
      });
    });

    await waitFor(() => expect(result.current.policyForm.company_id).toBe('1'));
    await waitFor(() => expect(result.current.policyForm.department_id).toBe(''));
  });

  it('toggles policy groups while respecting policy state ownership', async () => {
    const { result } = renderHook(() =>
      useUserPolicyManagement({
        departments: [{ id: 11, company_id: 1, name: 'QA' }],
      })
    );

    act(() => {
      result.current.handleOpenPolicyModal({
        user_id: 'u-2',
        role: 'sub_admin',
        full_name: 'Sub A',
        company_id: 1,
        department_id: 11,
        manager_user_id: '',
        managed_kb_root_node_id: 'node-1',
        managed_kb_root_path: '/Root',
        group_ids: [7],
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
        can_change_password: true,
        status: 'active',
      });
    });

    act(() => {
      result.current.handleTogglePolicyGroup(9, true);
    });

    await waitFor(() => expect(result.current.policyForm.group_ids).toEqual([7, 9]));
  });
});
