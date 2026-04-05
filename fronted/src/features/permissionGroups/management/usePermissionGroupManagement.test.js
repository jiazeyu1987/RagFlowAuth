import { renderHook, waitFor } from '@testing-library/react';
import usePermissionGroupManagement from './usePermissionGroupManagement';
import { permissionGroupsApi } from '../api';

jest.mock('../api', () => ({
  permissionGroupsApi: {
    list: jest.fn(),
    listGroupFolders: jest.fn(),
    listKnowledgeTree: jest.fn(),
    listChats: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    remove: jest.fn(),
    createFolder: jest.fn(),
    updateFolder: jest.fn(),
    removeFolder: jest.fn(),
  },
}));

describe('usePermissionGroupManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    permissionGroupsApi.list.mockResolvedValue([
      {
        group_id: 1,
        group_name: 'Quality',
        folder_id: null,
        accessible_kbs: [],
        accessible_kb_nodes: [],
        accessible_chats: [],
        accessible_tools: [],
      },
    ]);
    permissionGroupsApi.listGroupFolders.mockResolvedValue({
      folders: [{ id: 'folder-1', name: 'Team Folder', parent_id: null }],
      group_bindings: { '1': 'folder-1' },
      root_group_count: 0,
    });
    permissionGroupsApi.listKnowledgeTree.mockResolvedValue({
      nodes: [{ id: 'node-1', name: 'Root', parent_id: '', path: '/Root' }],
      datasets: [{ id: 'kb-1', name: 'KB 1', node_path: '/Root' }],
      bindings: {},
    });
    permissionGroupsApi.listChats.mockResolvedValue([
      { id: 'chat-1', name: 'Visible Chat' },
      { id: 'chat-2', name: '\u5927\u6a21\u578b' },
    ]);
  });

  it('loads unwrapped API data and filters hidden chats from state', async () => {
    const { result } = renderHook(() => usePermissionGroupManagement());

    await waitFor(() => {
      expect(permissionGroupsApi.list).toHaveBeenCalled();
      expect(permissionGroupsApi.listGroupFolders).toHaveBeenCalled();
      expect(permissionGroupsApi.listKnowledgeTree).toHaveBeenCalled();
      expect(permissionGroupsApi.listChats).toHaveBeenCalled();
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.groups).toEqual([
      expect.objectContaining({
        group_id: 1,
        folder_id: 'folder-1',
      }),
    ]);
    expect(result.current.folderPath[0]).toEqual(
      expect.objectContaining({
        id: '',
      })
    );
    expect(result.current.knowledgeDatasetItems).toEqual([
      expect.objectContaining({ id: 'kb-1', name: 'KB 1' }),
    ]);
    expect(result.current.chatAgents).toEqual([{ id: 'chat-1', name: 'Visible Chat' }]);
    expect(result.current.editingGroup).toEqual(expect.objectContaining({ group_id: 1 }));
  });
});
