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

const LABELS = {
  refresh: '\u5237\u65b0',
  createFolder: '\u65b0\u5efa\u6587\u4ef6\u5939',
  renameFolder: '\u91cd\u547d\u540d\u6587\u4ef6\u5939',
  deleteFolder: '\u5220\u9664\u6587\u4ef6\u5939',
  createGroup: '\u65b0\u5efa\u5206\u7ec4',
};

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
  };
}

describe('PermissionGroupManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders toolbar buttons with accessible names and keeps icon labels hidden', () => {
    usePermissionGroupManagement.mockReturnValue(buildHookState());

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

  it('disables folder rename and delete when root is selected and keeps other actions clickable', () => {
    const hookState = buildHookState();
    usePermissionGroupManagement.mockReturnValue(hookState);

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
    expect(hookState.startCreateGroup).toHaveBeenCalledTimes(1);
  });
});
