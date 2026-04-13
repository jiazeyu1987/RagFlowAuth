import { act, renderHook } from '@testing-library/react';

import usePermissionGroupManagement from './usePermissionGroupManagement';
import usePermissionGroupManagementPage from './usePermissionGroupManagementPage';
import { useAuth } from '../../../hooks/useAuth';

jest.mock('./usePermissionGroupManagement', () => jest.fn());
jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

const buildManagementState = (overrides = {}) => ({
  groups: [],
  loading: false,
  saving: false,
  error: '',
  hint: '',
  currentFolderId: 'root',
  selectedFolderId: 'root',
  expandedFolderIds: [],
  searchKeyword: '',
  selectedItem: null,
  dropTargetFolderId: null,
  mode: '',
  formData: {},
  editingGroup: null,
  folderIndexes: { byId: new Map(), childrenByParent: new Map() },
  knowledgeDatasetItems: [],
  chatAgents: [],
  setSearchKeyword: jest.fn(),
  setExpandedFolderIds: jest.fn(),
  setSelectedItem: jest.fn(),
  setFormData: jest.fn(),
  fetchAll: jest.fn(),
  createFolder: jest.fn(),
  renameFolder: jest.fn(),
  deleteFolder: jest.fn(),
  startCreateGroup: jest.fn(),
  viewGroup: jest.fn(),
  activateGroup: jest.fn(),
  saveForm: jest.fn(),
  cancelEdit: jest.fn(),
  removeGroup: jest.fn(),
  toggleKbAuth: jest.fn(),
  toggleChatAuth: jest.fn(),
  openFolder: jest.fn(),
  onDragOverFolder: jest.fn(),
  onDropFolder: jest.fn(),
  onDragLeaveFolder: jest.fn(),
  startGroupDrag: jest.fn(),
  endGroupDrag: jest.fn(),
  ...overrides,
});

describe('usePermissionGroupManagementPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ user: { user_id: 'u-1' } });
    usePermissionGroupManagement.mockReturnValue(buildManagementState());
  });

  it('clears pending delete state and deletes through the feature hook without a second confirm prompt', async () => {
    const removeGroup = jest.fn().mockResolvedValue(undefined);
    usePermissionGroupManagement.mockReturnValue(
      buildManagementState({
        removeGroup,
      })
    );

    const { result } = renderHook(() => usePermissionGroupManagementPage());
    const group = { group_id: 7, group_name: 'QA' };

    act(() => {
      result.current.handleRequestDeleteGroup(group);
    });

    expect(result.current.pendingDeleteGroup).toEqual(group);

    await act(async () => {
      await result.current.handleConfirmDeleteGroup();
    });

    expect(removeGroup).toHaveBeenCalledWith(group, { skipConfirm: true });
    expect(result.current.pendingDeleteGroup).toBe(null);
  });

  it('exposes editable-folder state and clears pending delete before starting create mode', () => {
    const startCreateGroup = jest.fn();
    usePermissionGroupManagement.mockReturnValue(
      buildManagementState({
        currentFolderId: 'folder-1',
        selectedFolderId: 'folder-1',
        folderIndexes: {
          byId: new Map([['folder-1', { id: 'folder-1', created_by: 'u-1' }]]),
          childrenByParent: new Map(),
        },
        startCreateGroup,
      })
    );

    const { result } = renderHook(() => usePermissionGroupManagementPage());

    act(() => {
      result.current.handleRequestDeleteGroup({ group_id: 3, group_name: 'Ops' });
    });

    expect(result.current.hasEditableFolder).toBe(true);
    expect(result.current.canCreateFolder).toBe(true);

    act(() => {
      result.current.handleCreateGroup();
    });

    expect(startCreateGroup).toHaveBeenCalledTimes(1);
    expect(result.current.pendingDeleteGroup).toBe(null);
  });

  it('treats other users folders as visible but read-only', () => {
    usePermissionGroupManagement.mockReturnValue(
      buildManagementState({
        currentFolderId: 'folder-2',
        selectedFolderId: 'folder-2',
        folderIndexes: {
          byId: new Map([['folder-2', { id: 'folder-2', created_by: 'u-other' }]]),
          childrenByParent: new Map(),
        },
      })
    );

    const { result } = renderHook(() => usePermissionGroupManagementPage());

    expect(result.current.hasEditableFolder).toBe(false);
    expect(result.current.canCreateFolder).toBe(false);
  });
});
