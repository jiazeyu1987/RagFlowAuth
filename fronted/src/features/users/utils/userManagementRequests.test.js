import {
  buildCreateUserRequest,
  buildDisableUserUpdateRequest,
  buildEnableUserUpdateRequest,
  buildPolicyUpdateRequest,
  parseRootDirectoryCreateRequest,
} from './userManagementRequests';

describe('userManagementRequests', () => {
  it('builds a normalized create-user request', () => {
    expect(
      buildCreateUserRequest({
        draft: {
          user_type: 'normal',
          username: 'emp-001',
          employee_user_id: 'emp-001',
          full_name: 'Alice',
          company_id: '1',
          department_id: '11',
          manager_user_id: 'sub-1',
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
        },
        kbDirectoryNodes: [],
      })
    ).toMatchObject({
      role: 'viewer',
      company_id: 1,
      department_id: 11,
      manager_user_id: 'sub-1',
      max_login_sessions: 3,
      idle_timeout_minutes: 120,
      group_ids: [],
      managed_kb_root_node_id: null,
    });
  });

  it('builds a policy update request with disable-until state applied', () => {
    expect(
      buildPolicyUpdateRequest({
        policyForm: {
          user_type: 'sub_admin',
          full_name: 'Sub Admin',
          company_id: '1',
          department_id: '11',
          managed_kb_root_node_id: 'node-1',
          group_ids: [7],
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
          can_change_password: true,
          disable_account: true,
          disable_mode: 'until',
          disable_until_date: '2099-12-31',
        },
        policyUser: { role: 'viewer' },
        kbDirectoryNodes: [{ id: 'node-1' }],
        nowMs: new Date('2099-01-01T00:00:00Z').getTime(),
      })
    ).toMatchObject({
      role: 'sub_admin',
      company_id: 1,
      department_id: 11,
      managed_kb_root_node_id: 'node-1',
      group_ids: [7],
      status: 'active',
      disable_login_enabled: true,
    });
  });

  it('parses root-directory create requests for admin and sub-admin actors', () => {
    expect(parseRootDirectoryCreateRequest({ companyId: '', name: 'Root', isAdminUser: true })).toEqual({
      errorCode: 'company_required',
    });

    expect(parseRootDirectoryCreateRequest({ companyId: 1, name: '  ', isAdminUser: true })).toEqual({
      errorCode: 'name_required',
    });

    expect(parseRootDirectoryCreateRequest({ companyId: 1, name: ' Root ', isAdminUser: true })).toEqual({
      errorCode: null,
      normalizedCompanyId: 1,
      payload: { name: 'Root', parent_id: null },
      requestOptions: { companyId: 1 },
    });

    expect(parseRootDirectoryCreateRequest({ companyId: 1, name: 'Root', isAdminUser: false })).toEqual({
      errorCode: null,
      normalizedCompanyId: 1,
      payload: { name: 'Root', parent_id: null },
      requestOptions: { companyId: undefined },
    });
  });

  it('builds disable and enable update payloads', () => {
    expect(buildDisableUserUpdateRequest({ mode: 'immediate' })).toEqual({
      status: 'inactive',
      disable_login_enabled: false,
      disable_login_until_ms: null,
    });

    expect(
      buildDisableUserUpdateRequest({
        mode: 'until',
        untilDate: '2099-12-31',
        nowMs: new Date('2099-01-01T00:00:00Z').getTime(),
      })
    ).toMatchObject({
      status: 'active',
      disable_login_enabled: true,
    });

    expect(buildEnableUserUpdateRequest()).toEqual({
      status: 'active',
      disable_login_enabled: false,
      disable_login_until_ms: null,
    });
  });
});
