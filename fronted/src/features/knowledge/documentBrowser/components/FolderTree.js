import React from 'react';
import { ROOT, TEXT } from '../constants';

export default function FolderTree({
  indexes,
  currentFolderId,
  expandedFolderIds,
  onToggleExpand,
  onOpenFolder,
  visibleNodeIds,
}) {
  const renderFolder = (folder, depth) => {
    const children = (indexes.childrenByParent.get(folder.id) || []).filter((node) => visibleNodeIds.has(node.id));
    const hasChildren = children.length > 0;
    const isExpanded = expandedFolderIds.includes(folder.id);
    const isCurrent = currentFolderId === folder.id;

    return (
      <div key={folder.id}>
        <div
          style={{
            marginLeft: depth * 16,
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 6px',
            background: isCurrent ? '#dbeafe' : 'transparent',
          }}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggleExpand(folder.id)}
            style={{
              width: 14,
              border: 'none',
              background: 'transparent',
              cursor: hasChildren ? 'pointer' : 'default',
              color: '#6b7280',
              padding: 0,
            }}
          >
            {hasChildren ? (isExpanded ? '▾' : '▸') : ''}
          </button>
          <button
            type="button"
            onClick={() => onOpenFolder(folder.id)}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}
            title={folder.path || folder.name}
          >
            {'📁 '} {folder.name || TEXT.folder}
          </button>
        </div>
        {isExpanded && children.map((child) => renderFolder(child, depth + 1))}
      </div>
    );
  };

  const roots = (indexes.childrenByParent.get(ROOT) || []).filter((node) => visibleNodeIds.has(node.id));
  return (
    <div>
      <div style={{ borderRadius: 6, padding: '3px 6px', marginBottom: 6, background: currentFolderId === ROOT ? '#dbeafe' : 'transparent' }}>
        <button
          type="button"
          onClick={() => onOpenFolder(ROOT)}
          style={{ border: 'none', background: 'transparent', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}
        >
          {'🖥️ '} {TEXT.root}
        </button>
      </div>
      {roots.map((folder) => renderFolder(folder, 0))}
      {!roots.length ? <div style={{ color: '#6b7280', fontSize: 13 }}>{TEXT.noKb}</div> : null}
    </div>
  );
}
