import React from 'react';
import { ROOT } from '../constants';

export default function DirectoryTreeView({
  indexes,
  currentDirId,
  selectedNodeId,
  expanded,
  onToggle,
  onOpen,
  dropTargetNodeId,
  onDragOverNode,
  onDropNode,
  onDragLeaveNode,
}) {
  const renderNode = (node, depth) => {
    const id = String(node?.id || '');
    const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_');
    const children = indexes.childrenByParent.get(id) || [];
    const hasChildren = children.length > 0;
    const isExpanded = expanded.includes(id);

    return (
      <div key={id}>
        <div
          className="browser-med-folder-row"
          style={{
            marginLeft: depth * 16,
            background:
              dropTargetNodeId === id ? '#dcfce7' : currentDirId === id ? '#dbeafe' : selectedNodeId === id ? '#eff6ff' : 'transparent',
          }}
          onDragOver={(event) => onDragOverNode(event, id)}
          onDrop={(event) => onDropNode(event, id)}
          onDragLeave={(event) => onDragLeaveNode(event, id)}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggle(id)}
            data-testid={`kbs-tree-toggle-${safeId}`}
            className="browser-med-folder-toggle"
            style={{ cursor: hasChildren ? 'pointer' : 'default' }}
          >
            {hasChildren ? (isExpanded ? '-' : '+') : ''}
          </button>
          <button
            type="button"
            onClick={() => onOpen(id)}
            data-testid={`kbs-tree-node-${safeId}`}
            className="browser-med-folder-root-btn"
            title={node.path || node.name}
          >
            {`目录 ${node.name || '（未命名目录）'}`}
          </button>
        </div>

        {isExpanded && children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  const roots = indexes.childrenByParent.get(ROOT) || [];

  return (
    <div data-testid="kbs-tree">
      <div
        className="browser-med-folder-row"
        style={{ background: dropTargetNodeId === ROOT ? '#dcfce7' : currentDirId === ROOT ? '#dbeafe' : 'transparent', marginBottom: 6 }}
        onDragOver={(event) => onDragOverNode(event, ROOT)}
        onDrop={(event) => onDropNode(event, ROOT)}
        onDragLeave={(event) => onDragLeaveNode(event, ROOT)}
      >
        <button
          type="button"
          onClick={() => onOpen(ROOT)}
          data-testid="kbs-tree-root"
          className="browser-med-folder-root-btn"
        >
          根目录
        </button>
      </div>

      {roots.map((node) => renderNode(node, 0))}
      {!roots.length ? <div className="medui-subtitle">暂无目录</div> : null}
    </div>
  );
}
