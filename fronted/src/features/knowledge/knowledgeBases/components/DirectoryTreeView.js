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
          style={{
            marginLeft: depth * 16,
            borderRadius: 6,
            background:
              dropTargetNodeId === id ? '#dcfce7' : currentDirId === id ? '#dbeafe' : selectedNodeId === id ? '#eff6ff' : 'transparent',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 6px',
          }}
          onDragOver={(event) => onDragOverNode(event, id)}
          onDrop={(event) => onDropNode(event, id)}
          onDragLeave={(event) => onDragLeaveNode(event, id)}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggle(id)}
            data-testid={`kbs-tree-toggle-${safeId}`}
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
          <button
            type="button"
            onClick={() => onOpen(id)}
            data-testid={`kbs-tree-node-${safeId}`}
            style={{ border: 'none', background: 'transparent', padding: 0, textAlign: 'left', cursor: 'pointer', width: '100%' }}
            title={node.path || node.name}
          >
            📁 {node.name || '(未命名目录)'}
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
        style={{
          borderRadius: 6,
          background: dropTargetNodeId === ROOT ? '#dcfce7' : currentDirId === ROOT ? '#dbeafe' : 'transparent',
          padding: '3px 6px',
          marginBottom: 6,
        }}
        onDragOver={(event) => onDragOverNode(event, ROOT)}
        onDrop={(event) => onDropNode(event, ROOT)}
        onDragLeave={(event) => onDragLeaveNode(event, ROOT)}
      >
        <button
          type="button"
          onClick={() => onOpen(ROOT)}
          data-testid="kbs-tree-root"
          style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer', width: '100%', textAlign: 'left' }}
        >
          🗂️ 根目录
        </button>
      </div>

      {roots.map((node) => renderNode(node, 0))}
      {!roots.length ? <div style={{ color: '#6b7280', fontSize: 13 }}>暂无目录</div> : null}
    </div>
  );
}
