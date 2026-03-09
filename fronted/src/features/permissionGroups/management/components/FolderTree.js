import React from 'react';
import { ROOT } from '../constants';

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

export default function FolderTree({
  indexes,
  currentFolderId,
  selectedFolderId,
  expanded,
  dropTargetFolderId,
  onToggleExpand,
  onOpenFolder,
  onDragOverFolder,
  onDropFolder,
  onDragLeaveFolder,
}) {
  const renderFolder = (folder, depth) => {
    const id = folder.id;
    const children = indexes.childrenByParent.get(id) || [];
    const hasChildren = children.length > 0;
    const isExpanded = expanded.includes(id);
    const isCurrent = currentFolderId === id;
    const isSelected = selectedFolderId === id;

    return (
      <div key={id}>
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
                : isCurrent
                  ? '#dbeafe'
                  : isSelected
                    ? '#eff6ff'
                    : 'transparent',
          }}
          onDragOver={(event) => onDragOverFolder(event, id)}
          onDrop={(event) => onDropFolder(event, id)}
          onDragLeave={(event) => onDragLeaveFolder(event, id)}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggleExpand(id)}
            style={{
              width: 14,
              border: 'none',
              background: 'transparent',
              cursor: hasChildren ? 'pointer' : 'default',
              color: '#6b7280',
              padding: 0,
            }}
          >
            {hasChildren ? (isExpanded ? '-' : '+') : ''}
          </button>
          <RowButton onClick={() => onOpenFolder(id)} title={folder.path || folder.name}>
            [Folder] {folder.name || '(Unnamed folder)'}
          </RowButton>
        </div>
        {isExpanded && children.map((child) => renderFolder(child, depth + 1))}
      </div>
    );
  };

  const roots = indexes.childrenByParent.get(ROOT) || [];

  return (
    <div>
      <div
        style={{
          borderRadius: 6,
          padding: '3px 6px',
          marginBottom: 6,
          background:
            dropTargetFolderId === ROOT
              ? '#dcfce7'
              : currentFolderId === ROOT
                ? '#dbeafe'
                : 'transparent',
        }}
        onDragOver={(event) => onDragOverFolder(event, ROOT)}
        onDrop={(event) => onDropFolder(event, ROOT)}
        onDragLeave={(event) => onDragLeaveFolder(event, ROOT)}
      >
        <RowButton onClick={() => onOpenFolder(ROOT)}>[Root]</RowButton>
      </div>
      {roots.map((folder) => renderFolder(folder, 0))}
      {!roots.length && <div style={{ color: '#6b7280', fontSize: 13 }}>No folders</div>}
    </div>
  );
}
