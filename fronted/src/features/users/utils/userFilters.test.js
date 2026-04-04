import { filterUsers } from './userFilters';

describe('userFilters', () => {
  const users = [
    {
      user_id: 'u-unassigned',
      username: 'alice',
      full_name: 'Alice',
      status: 'active',
      permission_groups: [],
    },
    {
      user_id: 'u-assigned-from-permissions',
      username: 'bob',
      full_name: 'Bob',
      status: 'active',
      permission_groups: [{ group_id: 7, group_name: '默认权限组' }],
    },
    {
      user_id: 'u-hidden-stale-group-id',
      username: 'carol',
      full_name: 'Carol',
      status: 'inactive',
      group_ids: ['8'],
      permission_groups: [],
    },
  ];

  it('filters users by unassigned permission groups', () => {
    const result = filterUsers(users, { assignment_status: 'unassigned' });

    expect(result.map((user) => user.user_id)).toEqual([
      'u-unassigned',
      'u-hidden-stale-group-id',
    ]);
  });

  it('filters users by assigned permission groups', () => {
    const result = filterUsers(users, { assignment_status: 'assigned' });

    expect(result.map((user) => user.user_id)).toEqual(['u-assigned-from-permissions']);
  });

  it('treats hidden stale group ids as unassigned when no visible permission group exists', () => {
    const result = filterUsers(users, { assignment_status: 'unassigned' });

    expect(result.map((user) => user.user_id)).toEqual([
      'u-unassigned',
      'u-hidden-stale-group-id',
    ]);
  });
});
