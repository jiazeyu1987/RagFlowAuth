import {
  buildManagedKbRootSelectionState,
  managedKbRootPathsOverlap,
  normalizeManagedKbRootPath,
} from './userManagedKbRoots';

describe('userManagedKbRoots', () => {
  it('normalizes managed-root paths into a stable slash-delimited form', () => {
    expect(normalizeManagedKbRootPath('')).toBe('/');
    expect(normalizeManagedKbRootPath('/')).toBe('/');
    expect(normalizeManagedKbRootPath(' /Root A/Child ')).toBe('/Root A/Child');
    expect(normalizeManagedKbRootPath('Root A//Child')).toBe('/Root A/Child');
  });

  it('detects overlapping managed-root paths only for ancestor or descendant scopes', () => {
    expect(managedKbRootPathsOverlap('/Root A', '/Root A')).toBe(true);
    expect(managedKbRootPathsOverlap('/Root A', '/Root A/Child')).toBe(true);
    expect(managedKbRootPathsOverlap('/Root A/Child', '/Root A')).toBe(true);
    expect(managedKbRootPathsOverlap('/Root A', '/Root AB')).toBe(false);
    expect(managedKbRootPathsOverlap('/Root A', '/Root B')).toBe(false);
  });

  it('hides other sub-admin occupied subtrees and keeps shared ancestors as disabled containers', () => {
    const nodes = [
      { id: 'node-root-a', name: 'Root A', parent_id: '', path: '/Root A' },
      { id: 'node-root-a-owned', name: 'Owned', parent_id: 'node-root-a', path: '/Root A/Owned' },
      { id: 'node-root-a-free', name: 'Free', parent_id: 'node-root-a', path: '/Root A/Free' },
      { id: 'node-root-b', name: 'Root B', parent_id: '', path: '/Root B' },
    ];
    const users = [
      {
        user_id: 'sub-admin-owned',
        role: 'sub_admin',
        status: 'active',
        company_id: 1,
        managed_kb_root_node_id: 'node-root-a-owned',
      },
    ];

    const state = buildManagedKbRootSelectionState({
      nodes,
      users,
      companyId: 1,
    });

    expect(state.nodes.map((node) => node.id)).toEqual([
      'node-root-a',
      'node-root-a-free',
      'node-root-b',
    ]);
    expect(state.disabledNodeIds).toEqual(['node-root-a']);
  });

  it('keeps the current policy user root visible by excluding that user from occupied-root filtering', () => {
    const nodes = [
      { id: 'node-root-a', name: 'Root A', parent_id: '', path: '/Root A' },
      { id: 'node-root-a-owned', name: 'Owned', parent_id: 'node-root-a', path: '/Root A/Owned' },
    ];
    const users = [
      {
        user_id: 'sub-admin-owned',
        role: 'sub_admin',
        status: 'active',
        company_id: 1,
        managed_kb_root_node_id: 'node-root-a-owned',
      },
    ];

    const state = buildManagedKbRootSelectionState({
      nodes,
      users,
      companyId: 1,
      excludeUserId: 'sub-admin-owned',
      selectedNodeId: 'node-root-a-owned',
    });

    expect(state.nodes.map((node) => node.id)).toEqual([
      'node-root-a',
      'node-root-a-owned',
    ]);
    expect(state.disabledNodeIds).toEqual([]);
  });

  it('ignores occupied assignments whose managed root can no longer be resolved', () => {
    const nodes = [
      { id: 'node-root-a', name: 'Root A', parent_id: '', path: '/Root A' },
      { id: 'node-root-b', name: 'Root B', parent_id: '', path: '/Root B' },
    ];
    const users = [
      {
        user_id: 'sub-admin-stale',
        role: 'sub_admin',
        status: 'active',
        company_id: 1,
        managed_kb_root_node_id: 'missing-node',
        managed_kb_root_path: null,
      },
    ];

    const state = buildManagedKbRootSelectionState({
      nodes,
      users,
      companyId: 1,
    });

    expect(state.nodes.map((node) => node.id)).toEqual(['node-root-a', 'node-root-b']);
    expect(state.disabledNodeIds).toEqual([]);
  });
});
