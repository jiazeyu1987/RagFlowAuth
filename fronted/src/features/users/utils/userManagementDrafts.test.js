import {
  applyManagedUserFieldChange,
  applyPolicyFormChange,
  toggleManagedUserDraftGroup,
  togglePolicyGroupSelection,
  toggleSelectedGroupIds,
} from './userManagementDrafts';

describe('userManagementDrafts', () => {
  it('clears company-scoped fields when create draft company changes', () => {
    expect(
      applyManagedUserFieldChange(
        {
          user_type: 'sub_admin',
          company_id: '1',
          department_id: '11',
          manager_user_id: 'sub-1',
          managed_kb_root_node_id: 'node-1',
        },
        'company_id',
        '2'
      )
    ).toMatchObject({
      company_id: '2',
      department_id: '',
      manager_user_id: '',
      managed_kb_root_node_id: '',
    });
  });

  it('drops create draft groups for non sub-admin users', () => {
    expect(
      toggleManagedUserDraftGroup(
        {
          user_type: 'normal',
          group_ids: [7],
        },
        9,
        true
      )
    ).toMatchObject({
      user_type: 'normal',
      group_ids: [],
    });
  });

  it('toggles create draft groups for sub-admin users without duplicates', () => {
    const added = toggleManagedUserDraftGroup({ user_type: 'sub_admin', group_ids: [7] }, 9, true);
    const removed = toggleManagedUserDraftGroup(added, 7, false);

    expect(added.group_ids).toEqual([7, 9]);
    expect(removed.group_ids).toEqual([9]);
  });

  it('resets company-scoped fields when policy draft company changes', () => {
    const next = applyPolicyFormChange(
      {
        user_type: 'sub_admin',
        company_id: '1',
        department_id: '11',
        manager_user_id: 'sub-1',
        managed_kb_root_node_id: 'node-1',
      },
      (prev) => ({ ...prev, company_id: '2' })
    );

    expect(next).toMatchObject({
      company_id: '2',
      department_id: '',
      manager_user_id: '',
      managed_kb_root_node_id: '',
    });
  });

  it('rejects policy group edits for admin targets and non sub-admin drafts', () => {
    expect(
      togglePolicyGroupSelection({
        draft: { user_type: 'sub_admin', group_ids: [7] },
        groupId: 9,
        checked: true,
        isPolicyAdminUser: true,
      })
    ).toMatchObject({ group_ids: [] });

    expect(
      togglePolicyGroupSelection({
        draft: { user_type: 'normal', group_ids: [7] },
        groupId: 9,
        checked: true,
        isPolicyAdminUser: false,
      })
    ).toMatchObject({ group_ids: [] });
  });

  it('toggles selected group ids without duplicates', () => {
    expect(toggleSelectedGroupIds([7], 9, true)).toEqual([7, 9]);
    expect(toggleSelectedGroupIds([7, 9], 7, false)).toEqual([9]);
    expect(toggleSelectedGroupIds([7], 7, true)).toEqual([7]);
  });
});
