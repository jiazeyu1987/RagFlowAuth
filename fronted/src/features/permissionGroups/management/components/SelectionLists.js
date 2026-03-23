import React, { useEffect, useMemo, useState } from 'react';
import { ROOT } from '../constants';

export function FolderSelectionList({
  title,
  items,
  selected,
  onToggle,
  emptyText,
  itemTestIdPrefix,
  emptyTestId,
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>
      {!items.length ? (
        <div data-testid={emptyTestId} style={{ color: '#6b7280', fontSize: 13 }}>
          {emptyText}
        </div>
      ) : (
        <div
          style={{
            maxHeight: 170,
            overflowY: 'auto',
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            padding: 8,
          }}
        >
          {items.map((item) => {
            const safeId = String(item.id).replace(/[^a-zA-Z0-9_-]/g, '_');
            const depth = Number(item?.depth || 0);
            return (
              <label
                key={item.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '4px 2px',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  data-testid={itemTestIdPrefix ? `${itemTestIdPrefix}-${safeId}` : undefined}
                  checked={selected.includes(item.id)}
                  onChange={() => onToggle(item.id)}
                />
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    paddingLeft: `${Math.max(0, depth) * 14}px`,
                  }}
                >
                  <span
                    aria-hidden="true"
                    style={{
                      width: 9,
                      height: 9,
                      borderRadius: 2,
                      border: '1px solid #94a3b8',
                      background: '#e2e8f0',
                      flexShrink: 0,
                    }}
                  />
                  <span>{item.name}</span>
                </span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function KnowledgeNodeTreeSelection({
  title,
  nodes,
  selected,
  onToggle,
  emptyText = '暂无知识目录',
  itemTestIdPrefix = 'pg-form-kb-node',
  emptyTestId,
}) {
  const tree = useMemo(() => {
    const childrenByParent = new Map();
    const byId = new Map();
    const source = Array.isArray(nodes) ? nodes : [];

    source.forEach((node) => {
      const id = String(node?.id || '').trim();
      if (!id) return;
      const parentId = String(node?.parent_id || '').trim() || ROOT;
      const item = {
        id,
        name: String(node?.name || '(未命名文件夹)').trim() || '(未命名文件夹)',
        parent_id: parentId,
        path: String(node?.path || ''),
      };
      byId.set(id, item);
      if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
      childrenByParent.get(parentId).push(item);
    });

    for (const arr of childrenByParent.values()) {
      arr.sort((a, b) => {
        const byPath = String(a.path || '').localeCompare(String(b.path || ''), 'zh-Hans-CN');
        if (byPath !== 0) return byPath;
        return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN');
      });
    }

    return { byId, childrenByParent };
  }, [nodes]);

  const [expandedIds, setExpandedIds] = useState([]);

  useEffect(() => {
    const parentExpanded = new Set();
    const selectedIds = Array.isArray(selected) ? selected : [];
    selectedIds.forEach((rawId) => {
      let current = tree.byId.get(String(rawId || '').trim());
      while (current && current.parent_id && current.parent_id !== ROOT) {
        parentExpanded.add(current.parent_id);
        current = tree.byId.get(current.parent_id);
      }
    });
    if (parentExpanded.size === 0) return;
    setExpandedIds((previous) => Array.from(new Set([...(previous || []), ...parentExpanded])));
  }, [selected, tree.byId]);

  const toggleExpand = (id) => {
    setExpandedIds((previous) =>
      previous.includes(id) ? previous.filter((value) => value !== id) : [...previous, id]
    );
  };

  const renderNode = (node, depth) => {
    const id = String(node.id || '');
    const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_');
    const children = tree.childrenByParent.get(id) || [];
    const hasChildren = children.length > 0;
    const expanded = expandedIds.includes(id);

    return (
      <div key={id}>
        <div
          style={{
            marginLeft: depth * 16,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 2px',
          }}
        >
          <button
            type="button"
            onClick={() => hasChildren && toggleExpand(id)}
            data-testid={`pg-tree-toggle-${safeId}`}
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
            {hasChildren ? (expanded ? '-' : '+') : ''}
          </button>
          <label
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
              minWidth: 0,
            }}
            title={node.path || node.name}
          >
            <input
              type="checkbox"
              data-testid={itemTestIdPrefix ? `${itemTestIdPrefix}-${safeId}` : undefined}
              checked={Array.isArray(selected) && selected.includes(id)}
              onChange={() => onToggle(id)}
            />
            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              📁 {node.name}
            </span>
          </label>
        </div>
        {expanded && children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  const roots = tree.childrenByParent.get(ROOT) || [];

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>
      {!roots.length ? (
        <div data-testid={emptyTestId} style={{ color: '#6b7280', fontSize: 13 }}>
          {emptyText}
        </div>
      ) : (
        <div
          style={{
            maxHeight: 220,
            overflowY: 'auto',
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            padding: 8,
          }}
          data-testid="pg-form-kb-node-tree"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 2px', marginBottom: 4 }}>
            <span style={{ width: 14, display: 'inline-block' }} />
            <span style={{ color: '#111827' }}>🗂️ 根目录</span>
          </div>
          {roots.map((node) => renderNode(node, 1))}
        </div>
      )}
    </div>
  );
}

export function ChatSelection({ chatAgents, selected, onToggle }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>对话权限</div>
      {!chatAgents.length ? (
        <div data-testid="pg-form-chat-empty" style={{ color: '#6b7280', fontSize: 13 }}>
          暂无对话
        </div>
      ) : (
        <div
          style={{
            maxHeight: 170,
            overflowY: 'auto',
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            padding: 8,
          }}
        >
          {chatAgents.map((chat) => {
            const safeId = String(chat.id).replace(/[^a-zA-Z0-9_-]/g, '_');
            return (
              <label
                key={chat.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '4px 2px',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  data-testid={`pg-form-chat-${safeId}`}
                  checked={selected.includes(chat.id)}
                  onChange={() => onToggle(chat.id)}
                />
                <span>
                  {chat.name} ({chat.type || 'chat'})
                </span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
