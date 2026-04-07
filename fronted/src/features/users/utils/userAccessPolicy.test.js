import {
  applyPolicyDisableState,
  buildCreateUserPayload,
  buildPolicyUpdatePayload,
  COMPANY_REQUIRED_MESSAGE,
  DISABLE_UNTIL_FUTURE_MESSAGE,
  DISABLE_UNTIL_REQUIRED_MESSAGE,
  IDLE_TIMEOUT_MESSAGE,
  KB_ROOT_REBIND_MESSAGE,
  KB_ROOT_REQUIRED_MESSAGE,
  MAX_LOGIN_SESSIONS_MESSAGE,
  normalizeDraftByUserType,
  normalizeGroupIds,
  parseDisableUntilDate,
  SUB_ADMIN_REQUIRED_MESSAGE,
  validateManagedUserPayload,
} from './userAccessPolicy';

describe('userAccessPolicy', () => {
  it('normalizes draft fields by user type', () => {
    expect(
      normalizeDraftByUserType({
        user_type: 'normal',
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: 'node-1',
        group_ids: [7, 8],
      })
    ).toEqual(
      expect.objectContaining({
        user_type: 'normal',
        managed_kb_root_node_id: '',
        group_ids: [],
      })
    );

    expect(
      normalizeDraftByUserType({
        user_type: 'sub_admin',
        manager_user_id: 'sub-1',
        group_ids: [7, '7', 8],
      })
    ).toEqual(
      expect.objectContaining({
        user_type: 'sub_admin',
        manager_user_id: '',
        group_ids: [7, 8],
      })
    );
  });

  it('normalizes unique positive permission group ids', () => {
    expect(normalizeGroupIds([7, '7', 0, 'x', 9])).toEqual([7, 9]);
  });

  it('builds create payloads for viewer and sub admin users', () => {
    expect(
      buildCreateUserPayload({
        username: 'viewer_a',
        password: 'secret',
        full_name: 'Viewer A',
        user_type: 'normal',
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: 'node-1',
        group_ids: [7],
        company_id: '1',
        department_id: '11',
        max_login_sessions: '3',
        idle_timeout_minutes: '120',
      })
    ).toEqual(
      expect.objectContaining({
        username: 'viewer_a',
        password: 'secret',
        role: 'viewer',
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: null,
        group_ids: [],
        company_id: 1,
        department_id: 11,
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      })
    );

    expect(
      buildCreateUserPayload({
        username: 'sub_a',
        user_type: 'sub_admin',
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: 'node-1',
        group_ids: [7, '7'],
        company_id: '1',
        department_id: '11',
        max_login_sessions: '3',
        idle_timeout_minutes: '120',
      })
    ).toEqual(
      expect.objectContaining({
        role: 'sub_admin',
        manager_user_id: null,
        managed_kb_root_node_id: 'node-1',
        group_ids: [7],
      })
    );
  });

  it('builds policy payloads and strips admin-only mutable fields', () => {
    expect(
      buildPolicyUpdatePayload({
        policyForm: {
          full_name: 'Admin A',
          company_id: '1',
          department_id: '11',
          user_type: 'sub_admin',
          manager_user_id: 'sub-1',
          managed_kb_root_node_id: 'node-1',
          group_ids: [7],
          max_login_sessions: '3',
          idle_timeout_minutes: '120',
          can_change_password: true,
        },
        policyUser: { role: 'admin' },
      })
    ).toEqual(
      expect.objectContaining({
        role: 'admin',
        company_id: 1,
        department_id: 11,
        can_change_password: true,
      })
    );
  });

  it('validates managed user payload boundaries', () => {
    const nodes = [{ id: 'node-1' }];

    expect(() =>
      validateManagedUserPayload({
        payload: {
          role: 'viewer',
          manager_user_id: 'sub-1',
          company_id: 1,
          department_id: 11,
          max_login_sessions: 0,
          idle_timeout_minutes: 120,
        },
        kbDirectoryNodes: nodes,
      })
    ).toThrow(MAX_LOGIN_SESSIONS_MESSAGE);

    expect(() =>
      validateManagedUserPayload({
        payload: {
          role: 'viewer',
          manager_user_id: 'sub-1',
          company_id: 1,
          department_id: 11,
          max_login_sessions: 3,
          idle_timeout_minutes: 0,
        },
        kbDirectoryNodes: nodes,
      })
    ).toThrow(IDLE_TIMEOUT_MESSAGE);

    expect(() =>
      validateManagedUserPayload({
        payload: {
          role: 'viewer',
          manager_user_id: 'sub-1',
          company_id: null,
          department_id: 11,
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
        },
        kbDirectoryNodes: nodes,
      })
    ).toThrow(COMPANY_REQUIRED_MESSAGE);

    expect(() =>
      validateManagedUserPayload({
        payload: {
          role: 'viewer',
          manager_user_id: null,
          company_id: 1,
          department_id: 11,
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
        },
        kbDirectoryNodes: nodes,
      })
    ).toThrow(SUB_ADMIN_REQUIRED_MESSAGE);

    expect(() =>
      validateManagedUserPayload({
        payload: {
          role: 'sub_admin',
          manager_user_id: null,
          managed_kb_root_node_id: null,
          company_id: 1,
          department_id: 11,
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
        },
        kbDirectoryNodes: nodes,
      })
    ).toThrow(KB_ROOT_REQUIRED_MESSAGE);

    expect(() =>
      validateManagedUserPayload({
        payload: {
          role: 'sub_admin',
          manager_user_id: null,
          managed_kb_root_node_id: 'node-x',
          company_id: 1,
          department_id: 11,
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
        },
        kbDirectoryNodes: nodes,
      })
    ).toThrow(KB_ROOT_REBIND_MESSAGE);
  });

  it('applies disable policy state strictly', () => {
    expect(
      applyPolicyDisableState({
        payload: { role: 'viewer' },
        policyForm: { disable_account: false, disable_mode: 'immediate', disable_until_date: '' },
      })
    ).toEqual(
      expect.objectContaining({
        status: 'active',
        disable_login_enabled: false,
        disable_login_until_ms: null,
      })
    );

    expect(() =>
      applyPolicyDisableState({
        payload: { role: 'viewer' },
        policyForm: { disable_account: true, disable_mode: 'until', disable_until_date: '' },
      })
    ).toThrow(DISABLE_UNTIL_REQUIRED_MESSAGE);

    expect(() =>
      applyPolicyDisableState({
        payload: { role: 'viewer' },
        policyForm: { disable_account: true, disable_mode: 'until', disable_until_date: '2020-01-01' },
        nowMs: new Date('2020-01-02T00:00:00').getTime(),
      })
    ).toThrow(DISABLE_UNTIL_FUTURE_MESSAGE);
  });

  it('parses disable-until dates to end-of-day timestamps', () => {
    expect(parseDisableUntilDate('')).toBeNull();
    expect(parseDisableUntilDate('2030-01-02')).toBe(new Date('2030-01-02T23:59:59').getTime());
  });
});
