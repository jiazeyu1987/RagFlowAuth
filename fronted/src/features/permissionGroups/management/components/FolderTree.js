import React, { useMemo } from 'react';
import { ROOT } from '../constants';

const ROOT_ICON = '\uD83D\uDDD2\uFE0F';
const FOLDER_ICON = '\uD83D\uDCC1';
const GROUP_ICON = '\uD83D\uDEE1\uFE0F';
const EXPANDED_ICON = '\u25BE';
const COLLAPSED_ICON = '\u25B8';
const ROOT_LABEL = '\u6839\u76ee\u5f55';
const EDIT_LABEL = '\u4fee\u6539';
const DELETE_LABEL = '\u5220\u9664';
const EMPTY_LABEL = '\u6682\u65e0\u6743\u9650\u8282\u70b9';

function RowButton({ children, ...props }) {
  return (
    <button
      type="button"
      style={{
        border: 'none',
        background: 'transparent',
        cursor: 'pointer',
        width: '100%',
        textAlign: 'left',
        padding: 0,
      }}
      {...props}
    >
      {children}
    </button>
  );
}

const actionButtonBaseStyle = {
  borderRadius: 6,
  cursor: 'pointer',
  padding: '2px 6px',
  fontSize: 12,
  flexShrink: 0,
};

function buildActionButtonStyle(borderColor, backgroundColor, textColor) {
  return {
    ...actionButtonBaseStyle,
    border: `1px solid ${borderColor}`,
    background: backgroundColor,
    color: textColor,
  };
}

function getGroupLabel(group) {
  return String(group?.group_name || '').trim() || '(Unnamed group)';
}

function getFolderLabel(folder) {
  return String(folder?.name || '').trim() || '(Unnamed folder)';
}

export default function FolderTree({
  indexes,
  groups,
  currentFolderId,
  selectedFolderId,
  selectedItem,
  expanded,
  dropTargetFolderId,
  onToggleExpand,
  onOpenFolder,
  onSelectItem,
  onViewGroup,
  onStartEditGroup,
  onRequestDeleteGroup,
  onDragOverFolder,
  onDropFolder,
  onDragLeaveFolder,
  onStartGroupDrag,
  onEndGroupDrag,
}) {
  const isGroupSelected = selectedItem?.kind === 'group';

  const groupsByFolder = useMemo(() => {
    const map = new Map();
    (groups || []).forEach((group) => {
      const folderId = group?.folder_id || ROOT;
      if (!map.has(folderId)) map.set(folderId, []);
      map.get(folderId).push(group);
    });
    for (const list of map.values()) {
      list.sort((left, right) => getGroupLabel(left).localeCompare(getGroupLabel(right), 'zh-Hans-CN'));
    }
    return map;
  }, [groups]);

  const renderGroup = (group, depth) => {
    const id = group.group_id;
    const safeId = String(id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
    const isSelected = selectedItem?.kind === 'group' && selectedItem?.id === id;
    const label = getGroupLabel(group);

    return (
      <div
        key={`group_${id}`}
        draggable
        onDragStart={(event) => onStartGroupDrag?.(event, id)}
        onDragEnd={() => onEndGroupDrag?.()}
        onClick={() => onViewGroup?.(group)}
        style={{
          marginLeft: depth * 16,
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '3px 6px',
          background: isSelected ? '#dbeafe' : 'transparent',
          cursor: 'pointer',
        }}
      >
        <span style={{ width: 14, display: 'inline-block', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <RowButton title={label}>
            {GROUP_ICON} {label}
          </RowButton>
        </div>
        <button
          type="button"
          data-testid={`pg-tree-edit-${safeId}`}
          onClick={(event) => {
            event.stopPropagation();
            onStartEditGroup?.(group);
          }}
          style={buildActionButtonStyle('#2563eb', '#eff6ff', '#1d4ed8')}
        >
          {EDIT_LABEL}
        </button>
        <button
          type="button"
          data-testid={`pg-tree-delete-${safeId}`}
          onClick={(event) => {
            event.stopPropagation();
            onSelectItem?.({ kind: 'group', id: group.group_id });
            onOpenFolder?.(group.folder_id || ROOT);
            onRequestDeleteGroup?.(group);
          }}
          style={buildActionButtonStyle('#ef4444', '#fef2f2', '#b91c1c')}
        >
          {DELETE_LABEL}
        </button>
      </div>
    );
  };

  const renderFolder = (folder, depth) => {
    const id = folder.id;
    const childFolders = indexes.childrenByParent.get(id) || [];
    const childGroups = groupsByFolder.get(id) || [];
    const hasChildren = childFolders.length > 0 || childGroups.length > 0;
    const isExpanded = expanded.includes(id);
    const isCurrent = currentFolderId === id;
    const isSelected = selectedFolderId === id || (selectedItem?.kind === 'folder' && selectedItem?.id === id);
    const isFolderHighlighted = !isGroupSelected && (isCurrent || isSelected);
    const label = getFolderLabel(folder);

    return (
      <div key={`folder_${id}`}>
        <div
          style={{
            marginLeft: depth * 16,
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 6px',
            background:
              dropTargetFolderId === id
                ? '#dcfce7'
                : isFolderHighlighted
                  ? '#dbeafe'
                  : 'transparent',
          }}
          onDragOver={(event) => onDragOverFolder?.(event, id)}
          onDrop={(event) => onDropFolder?.(event, id)}
          onDragLeave={(event) => onDragLeaveFolder?.(event, id)}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggleExpand?.(id)}
            style={{
              width: 14,
              border: 'none',
              background: 'transparent',
              cursor: hasChildren ? 'pointer' : 'default',
              color: '#6b7280',
              padding: 0,
              flexShrink: 0,
            }}
          >
            {hasChildren ? (isExpanded ? EXPANDED_ICON : COLLAPSED_ICON) : ''}
          </button>
          <RowButton
            onClick={() => {
              onSelectItem?.({ kind: 'folder', id });
              onOpenFolder?.(id);
            }}
            title={folder.path || label}
          >
            {FOLDER_ICON} {label}
          </RowButton>
        </div>
        {isExpanded && childFolders.map((child) => renderFolder(child, depth + 1))}
        {isExpanded && childGroups.map((group) => renderGroup(group, depth + 1))}
      </div>
    );
  };

  const rootFolders = indexes.childrenByParent.get(ROOT) || [];
  const rootGroups = groupsByFolder.get(ROOT) || [];
  const isRootSelected =
    !isGroupSelected &&
    (currentFolderId === ROOT || (selectedItem?.kind === 'folder' && selectedItem?.id === ROOT));

  return (
    <div>
      <div
        style={{
          borderRadius: 6,
          padding: '3px 6px',
          marginBottom: 6,
          background: dropTargetFolderId === ROOT ? '#dcfce7' : isRootSelected ? '#dbeafe' : 'transparent',
        }}
        onDragOver={(event) => onDragOverFolder?.(event, ROOT)}
        onDrop={(event) => onDropFolder?.(event, ROOT)}
        onDragLeave={(event) => onDragLeaveFolder?.(event, ROOT)}
      >
        <RowButton
          onClick={() => {
            onSelectItem?.({ kind: 'folder', id: ROOT });
            onOpenFolder?.(ROOT);
          }}
        >
          {ROOT_ICON} {ROOT_LABEL}
        </RowButton>
      </div>
      {rootFolders.map((folder) => renderFolder(folder, 0))}
      {rootGroups.map((group) => renderGroup(group, 0))}
      {!rootFolders.length && !rootGroups.length ? (
        <div style={{ color: '#6b7280', fontSize: 13 }}>{EMPTY_LABEL}</div>
      ) : null}
    </div>
  );
}
