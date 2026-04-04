import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import PermissionGroupManagement from './PermissionGroupManagement';
import usePermissionGroupManagement from '../features/permissionGroups/management/usePermissionGroupManagement';

jest.mock('../features/permissionGroups/management/usePermissionGroupManagement');
jest.mock('../features/permissionGroups/management/components/FolderTree', () => () => (
  <div data-testid="pg-folder-tree" />
));
jest.mock('../features/permissionGroups/management/components/GroupEditorForm', () => () => (
  <div data-testid="pg-editor-form" />
));

function buildHookState(overrides = {}) {
  return {
    groups: [{ group_id: 1, group_name: 'G1' }, { group_id: 2, group_name: 'G2' }],
    loading: false,
    saving: false,
    error: '',
    hint: '',
    currentFolderId: '',
    selectedFolderId: '',
    expandedFolderIds: [],
    searchKeyword: '',
    selectedItem: null,
    dropTargetFolderId: null,
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
    activateGroup: jest.fn(),
    saveForm: jest.fn(),
    cancelEdit: jest.fn(),
    removeGroup: jest.fn(),
    toggleKbAuth: jest.fn(),
    toggleChatAuth: jest.fn(),
    toggleToolAuth: jest.fn(),
    openFolder: jest.fn(),
    onDragOverFolder: jest.fn(),
    onDropFolder: jest.fn(),
    onDragLeaveFolder: jest.fn(),
    startGroupDrag: jest.fn(),
    endGroupDrag: jest.fn(),
    ...overrides,
  };
}

describe('PermissionGroupManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders five icon toolbar buttons with accessible names', () => {
    usePermissionGroupManagement.mockReturnValue(buildHookState());

    render(<PermissionGroupManagement />);

    expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新建文件夹' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重命名文件夹' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '删除文件夹' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新建分组' })).toBeInTheDocument();
    expect(screen.getByTestId('pg-create-open')).toBeInTheDocument();

    expect(screen.queryByText('刷新')).not.toBeInTheDocument();
    expect(screen.queryByText('新建文件夹')).not.toBeInTheDocument();
    expect(screen.queryByText('重命名文件夹')).not.toBeInTheDocument();
    expect(screen.queryByText('删除文件夹')).not.toBeInTheDocument();
    expect(screen.queryByText('新建分组')).not.toBeInTheDocument();
  });

  it('disables folder rename and delete when root is selected and keeps other actions clickable', () => {
    const hookState = buildHookState();
    usePermissionGroupManagement.mockReturnValue(hookState);

    render(<PermissionGroupManagement />);

    const refreshButton = screen.getByRole('button', { name: '刷新' });
    const createFolderButton = screen.getByRole('button', { name: '新建文件夹' });
    const renameButton = screen.getByRole('button', { name: '重命名文件夹' });
    const deleteButton = screen.getByRole('button', { name: '删除文件夹' });
    const createGroupButton = screen.getByRole('button', { name: '新建分组' });

    expect(renameButton).toBeDisabled();
    expect(deleteButton).toBeDisabled();

    fireEvent.click(refreshButton);
    fireEvent.click(createFolderButton);
    fireEvent.click(createGroupButton);

    expect(hookState.fetchAll).toHaveBeenCalledTimes(1);
    expect(hookState.createFolder).toHaveBeenCalledTimes(1);
    expect(hookState.startCreateGroup).toHaveBeenCalledTimes(1);
  });
});
