import React from 'react';

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
                <span>{item.name}</span>
              </label>
            );
          })}
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
