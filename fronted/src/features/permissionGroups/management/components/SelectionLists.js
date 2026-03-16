import React from 'react';

export function FolderSelectionList({
  title,
  items,
  selected,
  onToggle,
  emptyText,
  itemTestIdPrefix = '',
  emptyTestId = '',
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>
      {!items.length ? (
        <div data-testid={emptyTestId || undefined} className="admin-med-small">
          {emptyText}
        </div>
      ) : (
        <div style={{ maxHeight: 170, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
          {items.map((item) => (
            <label key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 2px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={selected.includes(item.id)}
                onChange={() => onToggle(item.id)}
                data-testid={itemTestIdPrefix ? `${itemTestIdPrefix}${String(item.id).replace(/[^a-zA-Z0-9_-]/g, '_')}` : undefined}
              />
              <span>{item.name}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatSelection({
  chatAgents,
  selected,
  onToggle,
  itemTestIdPrefix = '',
  emptyTestId = '',
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>问答访问权限</div>
      {!chatAgents.length ? (
        <div data-testid={emptyTestId || undefined} className="admin-med-small">
          暂无问答配置
        </div>
      ) : (
        <div style={{ maxHeight: 170, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
          {chatAgents.map((chat) => (
            <label key={chat.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 2px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={selected.includes(chat.id)}
                onChange={() => onToggle(chat.id)}
                data-testid={itemTestIdPrefix ? `${itemTestIdPrefix}${String(chat.id).replace(/[^a-zA-Z0-9_-]/g, '_')}` : undefined}
              />
              <span>{`${chat.name}（${chat.type || '对话'}）`}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
