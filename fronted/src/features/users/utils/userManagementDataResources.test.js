import {
  buildOrgDirectoryDisabledState,
  buildOrgDirectoryErrorState,
  buildOrgDirectoryState,
  buildPermissionGroupsLoadErrorLogArgs,
  buildPermissionGroupsLoadState,
  buildPermissionGroupsLoadErrorState,
  buildUsersLoadState,
  shouldLoadAssignableGroups,
  shouldLoadOrgDirectory,
} from './userManagementDataResources';

describe('userManagementDataResources', () => {
  it('only loads assignable groups for admin and sub-admin actors', () => {
    expect(shouldLoadAssignableGroups({ isAdminUser: true, isSubAdminUser: false })).toBe(true);
    expect(shouldLoadAssignableGroups({ isAdminUser: false, isSubAdminUser: true })).toBe(true);
    expect(shouldLoadAssignableGroups({ isAdminUser: false, isSubAdminUser: false })).toBe(false);
  });

  it('only loads the org directory for admin actors', () => {
    expect(shouldLoadOrgDirectory({ isAdminUser: true })).toBe(true);
    expect(shouldLoadOrgDirectory({ isAdminUser: false })).toBe(false);
  });

  it('builds the users, permission-group, and org-directory error states used by the hook', () => {
    expect(buildUsersLoadState([{ user_id: 'u-1' }])).toEqual({
      allUsers: [{ user_id: 'u-1' }],
      error: null,
    });

    expect(buildPermissionGroupsLoadErrorState()).toEqual({
      availableGroups: [],
      error: null,
    });

    expect(buildPermissionGroupsLoadState([{ group_id: 7 }])).toEqual({
      availableGroups: [{ group_id: 7 }],
      error: null,
    });

    expect(buildPermissionGroupsLoadErrorState('permission_groups_unavailable')).toEqual({
      availableGroups: [],
      error: 'permission_groups_unavailable',
    });

    expect(buildPermissionGroupsLoadErrorLogArgs('permission_groups_unavailable')).toEqual([
      'Failed to load permission groups:',
      'permission_groups_unavailable',
    ]);

    expect(buildOrgDirectoryDisabledState()).toEqual({
      companies: [],
      departments: [],
      error: null,
    });

    expect(buildOrgDirectoryErrorState('org_load_failed')).toEqual({
      companies: [],
      departments: [],
      error: 'org_load_failed',
    });
  });

  it('returns the no-company error when company data is missing', () => {
    expect(
      buildOrgDirectoryState({
        companyList: null,
        departmentList: [{ id: 11 }],
        noCompanyMessage: 'no company',
        noDepartmentMessage: 'no department',
      })
    ).toEqual({
      companies: [],
      departments: [{ id: 11 }],
      error: 'no company',
    });
  });

  it('returns the no-department error when department data is missing', () => {
    expect(
      buildOrgDirectoryState({
        companyList: [{ id: 1 }],
        departmentList: undefined,
        noCompanyMessage: 'no company',
        noDepartmentMessage: 'no department',
      })
    ).toEqual({
      companies: [{ id: 1 }],
      departments: [],
      error: 'no department',
    });
  });

  it('returns normalized companies and departments when both lists are present', () => {
    expect(
      buildOrgDirectoryState({
        companyList: [{ id: 1 }],
        departmentList: [{ id: 11 }],
        noCompanyMessage: 'no company',
        noDepartmentMessage: 'no department',
      })
    ).toEqual({
      companies: [{ id: 1 }],
      departments: [{ id: 11 }],
      error: null,
    });
  });
});
