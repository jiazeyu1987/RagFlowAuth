import {
  buildSubAdminOptions,
  buildUserDisplayLabel,
  buildUserManagementSubAdminOptions,
} from './userSubAdminOptions';

describe('userSubAdminOptions', () => {
  const users = [
    {
      user_id: 'sub-1',
      username: 'wangxin',
      full_name: '王鑫',
      role: 'sub_admin',
      status: 'active',
      company_id: 1,
    },
    {
      user_id: 'sub-2',
      username: 'uuid-user',
      full_name: '6567f115-49f7-49a3-86cf-2282ae823975',
      role: 'sub_admin',
      status: 'active',
      company_id: 1,
    },
    {
      user_id: 'sub-3',
      username: 'other-company',
      full_name: 'Other',
      role: 'sub_admin',
      status: 'active',
      company_id: 2,
    },
    {
      user_id: 'viewer-1',
      username: 'viewer',
      full_name: 'Viewer',
      role: 'viewer',
      status: 'active',
      company_id: 1,
    },
    {
      user_id: 'sub-4',
      username: 'inactive',
      full_name: 'Inactive',
      role: 'sub_admin',
      status: 'inactive',
      company_id: 1,
    },
  ];

  it('builds display labels without leaking uuid-like full names', () => {
    expect(buildUserDisplayLabel(users[0])).toBe('王鑫(wangxin)');
    expect(buildUserDisplayLabel(users[1])).toBe('uuid-user');
  });

  it('builds sub admin options filtered by company and excluded user', () => {
    expect(
      buildSubAdminOptions({
        users,
        companyId: 1,
        excludeUserId: 'sub-1',
      })
    ).toEqual([
      {
        value: 'sub-2',
        label: 'uuid-user',
        username: 'uuid-user',
        company_id: 1,
      },
    ]);
  });

  it('builds both create and policy sub-admin option sets for user management pages', () => {
    expect(
      buildUserManagementSubAdminOptions({
        users,
        createCompanyId: '1',
        policyCompanyId: '2',
        policyUserId: 'sub-3',
      })
    ).toEqual({
      subAdminOptions: [
        {
          value: 'sub-1',
          label: buildUserDisplayLabel(users[0]),
          username: 'wangxin',
          company_id: 1,
        },
        {
          value: 'sub-2',
          label: 'uuid-user',
          username: 'uuid-user',
          company_id: 1,
        },
      ],
      policySubAdminOptions: [],
    });
  });
});
