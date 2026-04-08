import React, { useMemo } from 'react';

import FolderTree from './FolderTree';
import {
  DeleteIcon,
  FolderAddIcon,
  RefreshIcon,
  RenameIcon,
  ToolbarIconButton,
  panelStyle,
} from '../permissionGroupManagementView';

export default function PermissionGroupSidebar({
  isMobile,
  hasEditableFolder,
  groups,
  currentFolderId,
  selectedFolderId,
  expandedFolderIds,
  searchKeyword,
  selectedItem,
  dropTargetFolderId,
  folderIndexes,
  setSearchKeyword,
  setExpandedFolderIds,
  setSelectedItem,
  fetchAll,
  createFolder,
  renameFolder,
  deleteFolder,
  openFolder,
  onDragOverFolder,
  onDropFolder,
  onDragLeaveFolder,
  startGroupDrag,
  endGroupDrag,
  handleViewGroup,
  handleEditGroup,
  handleRequestDeleteGroup,
}) {
  const toolbarButtons = useMemo(
    () => [
      {
        label: '刷新',
        icon: <RefreshIcon />,
        onClick: fetchAll,
        tone: 'neutral',
        testId: 'pg-toolbar-refresh',
      },
      {
        label: '新建文件夹',
        icon: <FolderAddIcon />,
        onClick: createFolder,
        tone: 'blue',
        testId: 'pg-toolbar-create-folder',
      },
      {
        label: '重命名文件夹',
        icon: <RenameIcon />,
        onClick: renameFolder,
        disabled: !hasEditableFolder,
        tone: 'orange',
        testId: 'pg-toolbar-rename-folder',
      },
      {
        label: '删除文件夹',
        icon: <DeleteIcon />,
        onClick: deleteFolder,
        disabled: !hasEditableFolder,
        tone: 'red',
        testId: 'pg-toolbar-delete-folder',
      },
    ],
    [createFolder, deleteFolder, fetchAll, hasEditableFolder, renameFolder]
  );

  return (
    <section style={panelStyle}>
      <div
        style={{
          padding: '10px 12px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <input
          value={searchKeyword}
          onChange={(event) => setSearchKeyword(event.target.value)}
          placeholder="筛选当前目录内容"
          style={{
            width: '100%',
            maxWidth: '100%',
            padding: '9px 10px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
            boxSizing: 'border-box',
          }}
        />
        <div
          data-testid="pg-toolbar-actions"
          style={{
            display: 'flex',
            gap: 10,
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          {toolbarButtons.map((button) => (
            <ToolbarIconButton
              key={button.label}
              label={button.label}
              icon={button.icon}
              onClick={button.onClick}
              disabled={button.disabled}
              tone={button.tone}
              testId={button.testId}
            />
          ))}
        </div>
        <div style={{ color: '#6b7280', fontSize: 12 }}>分组总数: {groups.length}</div>
      </div>
      <div style={{ padding: 10, maxHeight: isMobile ? 280 : 700, overflowY: 'auto' }}>
        <FolderTree
          indexes={folderIndexes}
          groups={groups}
          currentFolderId={currentFolderId}
          selectedFolderId={selectedFolderId}
          selectedItem={selectedItem}
          expanded={expandedFolderIds}
          dropTargetFolderId={dropTargetFolderId}
          onSelectItem={setSelectedItem}
          onToggleExpand={(id) =>
            setExpandedFolderIds((previous) =>
              previous.includes(id)
                ? previous.filter((value) => value !== id)
                : [...previous, id]
            )
          }
          onOpenFolder={openFolder}
          onDragOverFolder={onDragOverFolder}
          onDropFolder={onDropFolder}
          onDragLeaveFolder={onDragLeaveFolder}
          onViewGroup={handleViewGroup}
          onStartEditGroup={handleEditGroup}
          onRequestDeleteGroup={handleRequestDeleteGroup}
          onStartGroupDrag={startGroupDrag}
          onEndGroupDrag={endGroupDrag}
        />
      </div>
    </section>
  );
}
