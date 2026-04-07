import { buildPolicyFormFromUser, getUserPermissionGroupIds } from './userPolicyForm';

describe('userPolicyForm', () => {
  it('prefers explicit group_ids when present', () => {
    expect(getUserPermissionGroupIds({ group_ids: [7, 8], permission_groups: [{ group_id: 1 }] })).toEqual([7, 8]);
  });

  it('falls back to permission_groups when direct ids are absent', () => {
    expect(getUserPermissionGroupIds({ permission_groups: [{ group_id: 3 }, { group_id: 9 }] })).toEqual([3, 9]);
  });

  it('builds a policy form with a future disable date', () => {
    const form = buildPolicyFormFromUser(
      {
        role: 'viewer',
        full_name: 'Alice',
        company_id: 1,
        department_id: 11,
        manager_user_id: 'sub-1',
        permission_groups: [{ group_id: 7 }],
        managed_kb_root_node_id: 'node-1',
        max_login_sessions: 5,
        idle_timeout_minutes: 60,
        can_change_password: false,
        status: 'active',
        disable_login_enabled: true,
        disable_login_until_ms: new Date('2099-12-31T00:00:00Z').getTime(),
      },
      new Date('2099-01-01T00:00:00Z').getTime()
    );

    expect(form).toMatchObject({
      full_name: 'Alice',
      company_id: '1',
      department_id: '11',
      manager_user_id: 'sub-1',
      user_type: 'normal',
      managed_kb_root_node_id: 'node-1',
      group_ids: [7],
      max_login_sessions: 5,
      idle_timeout_minutes: 60,
      can_change_password: false,
      disable_account: true,
      disable_mode: 'until',
      disable_until_date: '2099-12-31',
    });
  });

  it('builds an immediate policy form for active sub-admin users', () => {
    const form = buildPolicyFormFromUser({
      role: 'sub_admin',
      full_name: 'Sub Admin',
      company_id: 2,
      department_id: 21,
      group_ids: [11],
      managed_kb_root_node_id: 'node-2',
      max_login_sessions: 3,
      idle_timeout_minutes: 120,
      can_change_password: true,
      status: 'active',
      disable_login_enabled: false,
    });

    expect(form).toMatchObject({
      user_type: 'sub_admin',
      group_ids: [11],
      disable_account: false,
      disable_mode: 'immediate',
      disable_until_date: '',
    });
  });
});
