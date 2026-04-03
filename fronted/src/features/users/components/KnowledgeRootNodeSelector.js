import React, { useMemo, useState } from 'react';

const ROOT = '';

const TEXT = {
  rootLabel: '\u6839\u76ee\u5f55',
  loading: '\u6b63\u5728\u52a0\u8f7d\u77e5\u8bc6\u5e93\u76ee\u5f55...',
  empty: '\u6682\u65e0\u53ef\u9009\u76ee\u5f55',
  emptyHint:
    '\u5f53\u524d\u516c\u53f8\u79df\u6237\u4e0b\u8fd8\u6ca1\u6709\u77e5\u8bc6\u5e93\u6839\u76ee\u5f55\uff0c\u53ef\u4ee5\u5148\u5728\u8fd9\u91cc\u521b\u5efa\u4e00\u4e2a\u9876\u7ea7\u76ee\u5f55\u3002',
  createPlaceholder: '\u8bf7\u8f93\u5165\u9876\u7ea7\u76ee\u5f55\u540d\u79f0',
  createButton: '\u521b\u5efa\u9876\u7ea7\u76ee\u5f55',
  creatingButton: '\u521b\u5efa\u4e2d...',
  unnamedFolder: '(\u672a\u547d\u540d\u76ee\u5f55)',
};

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
  if (!path || path === '/') return TEXT.rootLabel;
  return `${TEXT.rootLabel} ${path}`;
}

export default function KnowledgeRootNodeSelector({
  nodes,
  selectedNodeId,
  onSelect,
  disabled = false,
  loading = false,
  error = '',
  canCreateRoot = false,
  creatingRoot = false,
  createRootError = '',
  onCreateRoot,
}) {
  const indexes = useMemo(() => buildIndexes(nodes), [nodes]);
  const [expanded, setExpanded] = useState(() => new Set());
  const [rootName, setRootName] = useState('');

  const toggle = (nodeId) => {
    if (disabled) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  const handleCreateRoot = async () => {
    if (disabled || creatingRoot || typeof onCreateRoot !== 'function') return;
    const name = String(rootName || '').trim();
    if (!name) return;
    await onCreateRoot(name);
    setRootName('');
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
              <div style={{ fontWeight: 600, color: '#111827' }}>{node.name || TEXT.unnamedFolder}</div>
              <div style={{ fontSize: '0.82rem', color: '#6b7280', wordBreak: 'break-all' }}>{pathLabel(node)}</div>
            </div>
          </label>
        </div>
        {isExpanded ? children.map((child) => renderNode(child, depth + 1)) : null}
      </div>
    );
  };

  const roots = indexes.childrenByParent.get(ROOT) || [];
  const showCreateRoot = !loading && !error && roots.length === 0 && canCreateRoot;

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
      {loading ? <div style={{ color: '#6b7280' }}>{TEXT.loading}</div> : null}
      {!loading && error ? (
        <div style={{ color: '#dc2626' }} data-testid="users-kb-root-error">
          {error}
        </div>
      ) : null}
      {!loading && !error && roots.length === 0 ? <div style={{ color: '#6b7280' }}>{TEXT.empty}</div> : null}
      {showCreateRoot ? (
        <div
          style={{
            marginTop: 10,
            padding: 12,
            borderRadius: 8,
            border: '1px dashed #93c5fd',
            backgroundColor: '#eff6ff',
          }}
        >
          <div style={{ fontSize: '0.85rem', color: '#1d4ed8', marginBottom: 10 }}>{TEXT.emptyHint}</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              type="text"
              value={rootName}
              onChange={(event) => setRootName(event.target.value)}
              placeholder={TEXT.createPlaceholder}
              data-testid="users-kb-root-create-input"
              disabled={disabled || creatingRoot}
              style={{
                flex: '1 1 200px',
                minWidth: 0,
                padding: '8px 10px',
                border: '1px solid #bfdbfe',
                borderRadius: 6,
                backgroundColor: '#ffffff',
              }}
            />
            <button
              type="button"
              onClick={handleCreateRoot}
              data-testid="users-kb-root-create-button"
              disabled={disabled || creatingRoot || !String(rootName || '').trim()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 6,
                backgroundColor: disabled || creatingRoot || !String(rootName || '').trim() ? '#93c5fd' : '#2563eb',
                color: '#ffffff',
                cursor: disabled || creatingRoot || !String(rootName || '').trim() ? 'not-allowed' : 'pointer',
              }}
            >
              {creatingRoot ? TEXT.creatingButton : TEXT.createButton}
            </button>
          </div>
          {createRootError ? (
            <div
              style={{ marginTop: 10, color: '#dc2626', fontSize: '0.85rem' }}
              data-testid="users-kb-root-create-error"
            >
              {createRootError}
            </div>
          ) : null}
        </div>
      ) : null}
      {!loading && !error ? roots.map((node) => renderNode(node, 0)) : null}
    </div>
  );
}
