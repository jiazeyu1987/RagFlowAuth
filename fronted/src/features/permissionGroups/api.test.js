import { permissionGroupsApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('permissionGroupsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps successful envelopes into stable feature-level values', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ ok: true, data: [{ group_id: 1, group_name: 'G1' }] })
      .mockResolvedValueOnce({
        ok: true,
        data: { folders: [], group_bindings: {}, root_group_count: 0 },
      })
      .mockResolvedValueOnce({ ok: true, data: { group_id: 9 } })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true, data: { id: 'folder-1', name: 'Root Folder' } });

    await expect(permissionGroupsApi.list()).resolves.toEqual([{ group_id: 1, group_name: 'G1' }]);
    await expect(permissionGroupsApi.listGroupFolders()).resolves.toEqual({
      folders: [],
      group_bindings: {},
      root_group_count: 0,
    });
    await expect(permissionGroupsApi.create({ group_name: 'G9' })).resolves.toEqual({ group_id: 9 });
    await expect(permissionGroupsApi.remove(9)).resolves.toBeUndefined();
    await expect(permissionGroupsApi.createFolder({ name: 'Root Folder' })).resolves.toEqual({
      id: 'folder-1',
      name: 'Root Folder',
    });
  });

  it('fails fast when the backend envelope is not successful', async () => {
    httpClient.requestJson.mockResolvedValue({ ok: false, error: 'permission_denied' });

    await expect(permissionGroupsApi.listAssignable()).rejects.toThrow('permission_denied');
  });

  it('fails fast when the backend returns an invalid knowledge tree shape', async () => {
    httpClient.requestJson.mockResolvedValue({
      ok: true,
      data: { nodes: {}, datasets: [], bindings: {} },
    });

    await expect(permissionGroupsApi.listKnowledgeTree()).rejects.toThrow(
      'permission_groups_knowledge_tree_invalid_data'
    );
  });
});
