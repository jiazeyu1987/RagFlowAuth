import {
  prepareCreateUserSubmission,
  prepareDeleteUserSubmission,
  prepareDisableUserSubmission,
  prepareEnableUserSubmission,
  prepareGroupAssignmentSubmission,
  preparePolicyUpdateSubmission,
  prepareResetPasswordSubmission,
  prepareRootDirectoryCreateSubmission,
} from './userManagementSubmissions';

describe('userManagementSubmissions', () => {
  it('stops create submission when organization prerequisites are missing', () => {
    expect(
      prepareCreateUserSubmission({
        draft: {},
        kbDirectoryNodes: [],
        orgDirectoryError: 'org_error',
      })
    ).toEqual({ errorMessage: 'org_error' });
  });

  it('builds create submission payload when prerequisites are satisfied', () => {
    expect(
      prepareCreateUserSubmission({
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
        orgDirectoryError: null,
      })
    ).toMatchObject({
      payload: expect.objectContaining({
        role: 'viewer',
        company_id: 1,
        department_id: 11,
      }),
    });
  });

  it('stops policy submission when no target user or organization error exists', () => {
    expect(
      preparePolicyUpdateSubmission({
        policyUser: null,
        policyForm: {},
        kbDirectoryNodes: [],
        orgDirectoryError: null,
      })
    ).toEqual({ skipped: true });

    expect(
      preparePolicyUpdateSubmission({
        policyUser: { user_id: 'u-1' },
        policyForm: {},
        kbDirectoryNodes: [],
        orgDirectoryError: 'org_error',
      })
    ).toEqual({ errorMessage: 'org_error' });
  });

  it('builds policy update payload when prerequisites are satisfied', () => {
    expect(
      preparePolicyUpdateSubmission({
        policyUser: { user_id: 'u-1', role: 'viewer' },
        policyForm: {
          user_type: 'normal',
          company_id: '1',
          department_id: '11',
          manager_user_id: 'sub-1',
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
          can_change_password: true,
          disable_account: false,
        },
        kbDirectoryNodes: [],
        orgDirectoryError: null,
      })
    ).toMatchObject({
      userId: 'u-1',
      payload: expect.objectContaining({
        role: 'viewer',
        company_id: 1,
        department_id: 11,
      }),
    });
  });

  it('builds disable, reset-password, and group-assignment submissions', () => {
    expect(
      prepareDisableUserSubmission({
        disableTargetUser: null,
        disableMode: 'immediate',
        disableUntilDate: '',
      })
    ).toEqual({ skipped: true });

    expect(
      prepareDisableUserSubmission({
        disableTargetUser: { user_id: 'u-1' },
        disableMode: 'immediate',
        disableUntilDate: '',
      })
    ).toEqual({
      userId: 'u-1',
      payload: {
        status: 'inactive',
        disable_login_enabled: false,
        disable_login_until_ms: null,
      },
    });

    expect(prepareEnableUserSubmission({ targetUser: null })).toEqual({ skipped: true });

    expect(prepareEnableUserSubmission({ targetUser: { user_id: 'u-1' } })).toEqual({
      userId: 'u-1',
      payload: {
        status: 'active',
        disable_login_enabled: false,
        disable_login_until_ms: null,
      },
    });

    expect(prepareDeleteUserSubmission({ userId: '' })).toEqual({ skipped: true });

    expect(prepareDeleteUserSubmission({ userId: 'u-9' })).toEqual({
      userId: 'u-9',
    });

    expect(
      prepareResetPasswordSubmission({
        resetPasswordUser: { user_id: 'u-1' },
        resetPasswordValue: '',
        resetPasswordConfirm: '',
      })
    ).toEqual({ errorCode: 'password_required' });

    expect(
      prepareResetPasswordSubmission({
        resetPasswordUser: { user_id: 'u-1' },
        resetPasswordValue: 'a',
        resetPasswordConfirm: 'b',
      })
    ).toEqual({ errorCode: 'password_mismatch' });

    expect(
      prepareResetPasswordSubmission({
        resetPasswordUser: { user_id: 'u-1' },
        resetPasswordValue: 'secret',
        resetPasswordConfirm: 'secret',
      })
    ).toEqual({ userId: 'u-1', password: 'secret' });

    expect(
      prepareGroupAssignmentSubmission({
        editingGroupUser: { user_id: 'u-2' },
        selectedGroupIds: [7, 9],
      })
    ).toEqual({
      userId: 'u-2',
      payload: { group_ids: [7, 9] },
    });
  });

  it('prepares root-directory create submissions for validation and execution', () => {
    expect(
      prepareRootDirectoryCreateSubmission({
        companyId: '',
        name: 'Root',
        isAdminUser: true,
      })
    ).toEqual({ errorCode: 'company_required' });

    expect(
      prepareRootDirectoryCreateSubmission({
        companyId: 1,
        name: ' Root ',
        isAdminUser: true,
      })
    ).toEqual({
      errorCode: null,
      normalizedCompanyId: 1,
      payload: { name: 'Root', parent_id: null },
      requestOptions: { companyId: 1 },
    });
  });
});
