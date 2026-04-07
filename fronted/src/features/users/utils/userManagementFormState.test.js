import { DEFAULT_NEW_USER, DEFAULT_POLICY_FORM } from './constants';
import {
  buildClosedCreateUserState,
  buildClosedPolicyState,
  buildOpenedCreateUserState,
  buildOpenedPolicyState,
} from './userManagementFormState';

describe('userManagementFormState', () => {
  it('builds opened and closed create-user modal state', () => {
    const currentNewUser = { ...DEFAULT_NEW_USER, username: 'alice' };

    expect(buildOpenedCreateUserState(currentNewUser)).toEqual({
      showCreateModal: true,
      newUser: currentNewUser,
      createUserError: null,
    });
    expect(buildClosedCreateUserState()).toEqual({
      showCreateModal: false,
      newUser: DEFAULT_NEW_USER,
      createUserError: null,
    });
  });

  it('builds opened policy state from the target user', () => {
    expect(
      buildOpenedPolicyState({
        user_id: 'u-1',
        role: 'sub_admin',
        full_name: 'Alice',
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
      })
    ).toEqual(
      expect.objectContaining({
        showPolicyModal: true,
        policyUser: expect.objectContaining({ user_id: 'u-1' }),
        policyError: null,
        policyForm: expect.objectContaining({
          user_type: 'sub_admin',
          company_id: '1',
          department_id: '11',
          managed_kb_root_node_id: 'node-1',
          group_ids: [7],
        }),
      })
    );
  });

  it('builds closed policy state with the provided initial form', () => {
    const initialPolicyForm = { ...DEFAULT_POLICY_FORM, company_id: '2' };

    expect(buildClosedPolicyState(initialPolicyForm)).toEqual({
      showPolicyModal: false,
      policyUser: null,
      policyError: null,
      policyForm: initialPolicyForm,
    });
  });
});
