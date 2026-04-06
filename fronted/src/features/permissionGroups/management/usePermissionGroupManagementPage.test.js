import { act, renderHook } from '@testing-library/react';

import usePermissionGroupManagement from './usePermissionGroupManagement';
import usePermissionGroupManagementPage from './usePermissionGroupManagementPage';

jest.mock('./usePermissionGroupManagement', () => jest.fn());

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
        selectedFolderId: 'folder-1',
        startCreateGroup,
      })
    );

    const { result } = renderHook(() => usePermissionGroupManagementPage());

    act(() => {
      result.current.handleRequestDeleteGroup({ group_id: 3, group_name: 'Ops' });
    });

    expect(result.current.hasEditableFolder).toBe(true);

    act(() => {
      result.current.handleCreateGroup();
    });

    expect(startCreateGroup).toHaveBeenCalledTimes(1);
    expect(result.current.pendingDeleteGroup).toBe(null);
  });
});
