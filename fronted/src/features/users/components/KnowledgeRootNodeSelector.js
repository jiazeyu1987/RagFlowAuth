import React, { useMemo, useState } from 'react';

const ROOT = '';

function buildIndexes(nodes) {
  const byId = new Map();
  const childrenByParent = new Map();
  (Array.isArray(nodes) ? nodes : []).forEach((node) => {
    if (!node?.id) return;
    const id = String(node.id);
    const parentId = String(node.parent_id || ROOT);
    byId.set(id, node);
    if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
    childrenByParent.get(parentId).push(node);
  });
  for (const list of childrenByParent.values()) {
    list.sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || ''), 'zh-Hans-CN'));
  }
  return { byId, childrenByParent };
}

function pathLabel(node) {
  const path = String(node?.path || '').trim();
  if (!path || path === '/') return '根目录';
  return `根目录${path}`;
}

export default function KnowledgeRootNodeSelector({
  nodes,
  selectedNodeId,
  onSelect,
  disabled = false,
  loading = false,
  error = '',
}) {
  const indexes = useMemo(() => buildIndexes(nodes), [nodes]);
  const [expanded, setExpanded] = useState(() => new Set());

  const toggle = (nodeId) => {
    if (disabled) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  const renderNode = (node, depth) => {
    const id = String(node.id);
    const children = indexes.childrenByParent.get(id) || [];
    const hasChildren = children.length > 0;
    const isExpanded = expanded.has(id);
    const isSelected = String(selectedNodeId || '') === id;
    return (
      <div key={id}>
        <div
          style={{
            marginLeft: depth * 16,
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8,
            padding: '8px 10px',
            borderRadius: 8,
            backgroundColor: isSelected ? '#eff6ff' : 'transparent',
          }}
        >
          <button
            type="button"
            onClick={() => toggle(id)}
            disabled={disabled || !hasChildren}
            data-testid={`users-kb-root-toggle-${id}`}
            style={{
              width: 20,
              border: 'none',
              background: 'transparent',
              color: '#6b7280',
              cursor: disabled || !hasChildren ? 'default' : 'pointer',
              padding: 0,
              marginTop: 2,
            }}
          >
            {hasChildren ? (isExpanded ? '-' : '+') : ''}
          </button>
          <label
            style={{
              flex: 1,
              display: 'flex',
              gap: 10,
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.6 : 1,
            }}
          >
            <input
              type="radio"
              name="users-kb-root-node"
              checked={isSelected}
              disabled={disabled}
              onChange={() => onSelect?.(id)}
              data-testid={`users-kb-root-node-${id}`}
              style={{ marginTop: 2 }}
            />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, color: '#111827' }}>{node.name || '(未命名目录)'}</div>
              <div style={{ fontSize: '0.82rem', color: '#6b7280', wordBreak: 'break-all' }}>{pathLabel(node)}</div>
            </div>
          </label>
        </div>
        {isExpanded ? children.map((child) => renderNode(child, depth + 1)) : null}
      </div>
    );
  };

  const roots = indexes.childrenByParent.get(ROOT) || [];

  return (
    <div
      data-testid="users-kb-root-selector"
      style={{
        border: '1px solid #d1d5db',
        borderRadius: 8,
        padding: 12,
        backgroundColor: '#f9fafb',
        maxHeight: 240,
        overflowY: 'auto',
      }}
    >
      {loading ? <div style={{ color: '#6b7280' }}>加载知识库目录中...</div> : null}
      {!loading && error ? (
        <div style={{ color: '#dc2626' }} data-testid="users-kb-root-error">
          {error}
        </div>
      ) : null}
      {!loading && !error && roots.length === 0 ? <div style={{ color: '#6b7280' }}>暂无可选目录</div> : null}
      {!loading && !error ? roots.map((node) => renderNode(node, 0)) : null}
    </div>
  );
}
