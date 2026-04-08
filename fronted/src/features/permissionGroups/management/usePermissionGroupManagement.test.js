import { act, renderHook, waitFor } from '@testing-library/react';
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

  it('creates a permission group, reloads the list, and surfaces the saved group through the same hook contract', async () => {
    const createdGroup = {
      group_id: 2,
      group_name: 'Ops',
      folder_id: 'folder-1',
      accessible_kbs: [],
      accessible_kb_nodes: [],
      accessible_chats: [],
      accessible_tools: [],
    };

    permissionGroupsApi.create.mockResolvedValue({
      message: 'created',
      group_id: 2,
    });

    const { result } = renderHook(() => usePermissionGroupManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));

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
      createdGroup,
    ]);
    permissionGroupsApi.listGroupFolders.mockResolvedValue({
      folders: [{ id: 'folder-1', name: 'Team Folder', parent_id: null }],
      group_bindings: { '1': 'folder-1', '2': 'folder-1' },
      root_group_count: 0,
    });

    act(() => {
      result.current.startCreateGroup();
      result.current.setFormData((previous) => ({
        ...previous,
        group_name: 'Ops',
      }));
    });

    await act(async () => {
      await result.current.saveForm({
        preventDefault: jest.fn(),
      });
    });

    await waitFor(() => {
      expect(permissionGroupsApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          group_name: 'Ops',
          folder_id: 'folder-1',
        })
      );
      expect(result.current.hint).toBe('权限组已创建');
      expect(result.current.mode).toBe('view');
      expect(result.current.editingGroup).toEqual(expect.objectContaining({ group_id: 2 }));
    });
  });

  it('moves the dragged permission group to a new folder and clears drag state after drop', async () => {
    permissionGroupsApi.update.mockResolvedValue({
      message: 'updated',
    });

    const { result } = renderHook(() => usePermissionGroupManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));

    permissionGroupsApi.list.mockResolvedValue([
      {
        group_id: 1,
        group_name: 'Quality',
        folder_id: 'folder-2',
        accessible_kbs: [],
        accessible_kb_nodes: [],
        accessible_chats: [],
        accessible_tools: [],
      },
    ]);
    permissionGroupsApi.listGroupFolders.mockResolvedValue({
      folders: [
        { id: 'folder-1', name: 'Team Folder', parent_id: null },
        { id: 'folder-2', name: 'Archive', parent_id: null },
      ],
      group_bindings: { '1': 'folder-2' },
      root_group_count: 0,
    });

    const dragEvent = {
      dataTransfer: {
        setData: jest.fn(),
        effectAllowed: '',
      },
    };
    const dropEvent = {
      preventDefault: jest.fn(),
      dataTransfer: {
        getData: jest.fn(() => '1'),
      },
    };

    act(() => {
      result.current.startGroupDrag(dragEvent, 1);
    });

    expect(result.current.dragGroupId).toBe(1);

    await act(async () => {
      await result.current.onDropFolder(dropEvent, 'folder-2');
    });

    await waitFor(() => {
      expect(permissionGroupsApi.update).toHaveBeenCalledWith(1, { folder_id: 'folder-2' });
      expect(result.current.dragGroupId).toBe(null);
      expect(result.current.dropTargetFolderId).toBe(null);
      expect(result.current.formData.folder_id).toBe('folder-2');
      expect(result.current.hint).toBe('权限组已移动');
    });
  });
});
