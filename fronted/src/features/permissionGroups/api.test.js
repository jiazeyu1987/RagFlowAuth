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
      .mockResolvedValueOnce({ groups: [{ group_id: 1, group_name: 'G1' }] })
      .mockResolvedValueOnce({
        folder_snapshot: { folders: [], group_bindings: {}, root_group_count: 0 },
      })
      .mockResolvedValueOnce({ result: { message: 'permission_group_created', group_id: 9 } })
      .mockResolvedValueOnce({ result: { message: 'permission_group_deleted' } })
      .mockResolvedValueOnce({ folder: { id: 'folder-1', name: 'Root Folder' } });

    await expect(permissionGroupsApi.list()).resolves.toEqual([{ group_id: 1, group_name: 'G1' }]);
    await expect(permissionGroupsApi.listGroupFolders()).resolves.toEqual({
      folders: [],
      group_bindings: {},
      root_group_count: 0,
    });
    await expect(permissionGroupsApi.create({ group_name: 'G9' })).resolves.toEqual({
      message: 'permission_group_created',
      group_id: 9,
    });
    await expect(permissionGroupsApi.remove(9)).resolves.toEqual({
      message: 'permission_group_deleted',
    });
    await expect(permissionGroupsApi.createFolder({ name: 'Root Folder' })).resolves.toEqual({
      id: 'folder-1',
      name: 'Root Folder',
    });
  });

  it('propagates backend request failures without swallowing details', async () => {
    httpClient.requestJson.mockRejectedValue(new Error('permission_denied'));

    await expect(permissionGroupsApi.listAssignable()).rejects.toThrow('permission_denied');
  });

  it('fails fast when the backend returns an invalid knowledge tree shape', async () => {
    httpClient.requestJson.mockResolvedValue({
      knowledge_tree: { nodes: {}, datasets: [], bindings: {} },
    });

    await expect(permissionGroupsApi.listKnowledgeTree()).rejects.toThrow(
      'permission_groups_knowledge_tree_invalid_payload'
    );
  });

  it('fails fast when the backend returns an invalid create result payload', async () => {
    httpClient.requestJson.mockResolvedValue({
      result: { message: 'permission_group_created' },
    });

    await expect(permissionGroupsApi.create({ group_name: 'G9' })).rejects.toThrow(
      'permission_groups_create_invalid_payload'
    );
  });
});
