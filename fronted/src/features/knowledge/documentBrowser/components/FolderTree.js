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
        <div className={`browser-med-folder-row ${isCurrent ? 'is-current' : ''}`} style={{ marginLeft: depth * 16 }}>
          <button
            type="button"
            onClick={() => hasChildren && onToggleExpand(folder.id)}
            className="browser-med-folder-toggle"
            style={{ cursor: hasChildren ? 'pointer' : 'default' }}
          >
            {hasChildren ? (isExpanded ? '▾' : '▸') : ''}
          </button>
          <button
            type="button"
            onClick={() => onOpenFolder(folder.id)}
            className="browser-med-folder-root-btn"
            title={folder.path || folder.name}
          >
            {`${TEXT.folder}：${folder.name || TEXT.folder}`}
          </button>
        </div>
        {isExpanded && children.map((child) => renderFolder(child, depth + 1))}
      </div>
    );
  };

  const roots = (indexes.childrenByParent.get(ROOT) || []).filter((node) => visibleNodeIds.has(node.id));
  return (
    <div>
      <div className={`browser-med-folder-row ${currentFolderId === ROOT ? 'is-current' : ''}`} style={{ marginBottom: 6 }}>
        <button type="button" onClick={() => onOpenFolder(ROOT)} className="browser-med-folder-root-btn">
          {TEXT.root}
        </button>
      </div>
      {roots.map((folder) => renderFolder(folder, 0))}
      {!roots.length ? <div className="medui-subtitle">{TEXT.noKb}</div> : null}
    </div>
  );
}
