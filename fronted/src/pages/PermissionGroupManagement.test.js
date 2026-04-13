import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import PermissionGroupManagement from './PermissionGroupManagement';
import usePermissionGroupManagementPage from '../features/permissionGroups/management/usePermissionGroupManagementPage';

jest.mock('../features/permissionGroups/management/usePermissionGroupManagementPage', () => jest.fn());
jest.mock('../features/permissionGroups/management/components/FolderTree', () => () => (
  <div data-testid="pg-folder-tree" />
));
jest.mock('../features/permissionGroups/management/components/GroupEditorForm', () => () => (
  <div data-testid="pg-editor-form" />
));

const LABELS = {
  refresh: '刷新',
  createFolder: '新建文件夹',
  renameFolder: '重命名文件夹',
  deleteFolder: '删除文件夹',
  createGroup: '新建分组',
};

function buildHookState(overrides = {}) {
  return {
    isMobile: false,
    pendingDeleteGroup: null,
    hasEditableFolder: false,
    canCreateFolder: true,
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
    saveForm: jest.fn(),
    cancelEdit: jest.fn(),
    toggleKbAuth: jest.fn(),
    toggleChatAuth: jest.fn(),
    openFolder: jest.fn(),
    onDragOverFolder: jest.fn(),
    onDropFolder: jest.fn(),
    onDragLeaveFolder: jest.fn(),
    startGroupDrag: jest.fn(),
    endGroupDrag: jest.fn(),
    handleCreateGroup: jest.fn(),
    handleViewGroup: jest.fn(),
    handleEditGroup: jest.fn(),
    handleRequestDeleteGroup: jest.fn(),
    handleCancelDeleteGroup: jest.fn(),
    handleConfirmDeleteGroup: jest.fn(),
    ...overrides,
  };
}

describe('PermissionGroupManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders toolbar buttons with accessible names and keeps icon labels hidden', () => {
    usePermissionGroupManagementPage.mockReturnValue(buildHookState());

    render(<PermissionGroupManagement />);

    expect(screen.getByRole('button', { name: LABELS.refresh })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: LABELS.createFolder })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: LABELS.renameFolder })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: LABELS.deleteFolder })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: LABELS.createGroup })).toBeInTheDocument();
    expect(screen.getByTestId('pg-create-open')).toBeInTheDocument();

    expect(screen.queryByText(LABELS.refresh)).not.toBeInTheDocument();
    expect(screen.queryByText(LABELS.createFolder)).not.toBeInTheDocument();
    expect(screen.queryByText(LABELS.renameFolder)).not.toBeInTheDocument();
    expect(screen.queryByText(LABELS.deleteFolder)).not.toBeInTheDocument();
    expect(screen.getByText(LABELS.createGroup)).toBeInTheDocument();
  });

  it('disables folder rename and delete when no editable folder is selected and keeps other actions clickable', () => {
    const hookState = buildHookState({
      hasEditableFolder: false,
      canCreateFolder: true,
    });
    usePermissionGroupManagementPage.mockReturnValue(hookState);

    render(<PermissionGroupManagement />);

    const refreshButton = screen.getByRole('button', { name: LABELS.refresh });
    const createFolderButton = screen.getByRole('button', { name: LABELS.createFolder });
    const renameButton = screen.getByRole('button', { name: LABELS.renameFolder });
    const deleteButton = screen.getByRole('button', { name: LABELS.deleteFolder });
    const createGroupButton = screen.getByRole('button', { name: LABELS.createGroup });

    expect(renameButton).toBeDisabled();
    expect(deleteButton).toBeDisabled();

    fireEvent.click(refreshButton);
    fireEvent.click(createFolderButton);
    fireEvent.click(createGroupButton);

    expect(hookState.fetchAll).toHaveBeenCalledTimes(1);
    expect(hookState.createFolder).toHaveBeenCalledTimes(1);
    expect(hookState.handleCreateGroup).toHaveBeenCalledTimes(1);
  });

  it('disables create-folder when the current folder is read-only', () => {
    const hookState = buildHookState({
      canCreateFolder: false,
    });
    usePermissionGroupManagementPage.mockReturnValue(hookState);

    render(<PermissionGroupManagement />);

    const createFolderButton = screen.getByRole('button', { name: LABELS.createFolder });
    expect(createFolderButton).toBeDisabled();

    fireEvent.click(createFolderButton);

    expect(hookState.createFolder).not.toHaveBeenCalled();
  });

  it('renders pending delete confirmation actions and wires cancel and confirm callbacks', () => {
    const hookState = buildHookState({
      pendingDeleteGroup: { group_id: 9, group_name: 'Ops' },
    });
    usePermissionGroupManagementPage.mockReturnValue(hookState);

    render(<PermissionGroupManagement />);

    expect(screen.getByText('确认删除权限组“Ops”？')).toBeInTheDocument();

    fireEvent.click(screen.getByText('取消'));
    fireEvent.click(screen.getByTestId('pg-delete-confirm'));

    expect(hookState.handleCancelDeleteGroup).toHaveBeenCalledTimes(1);
    expect(hookState.handleConfirmDeleteGroup).toHaveBeenCalledTimes(1);
  });
});
