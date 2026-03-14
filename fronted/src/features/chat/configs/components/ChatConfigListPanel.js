import React from 'react';

export default function ChatConfigListPanel({
  panelStyle,
  chatLoading,
  chatListLength,
  isAdmin,
  onOpenCreate,
  chatFilter,
  onFilterChange,
  onRefresh,
  chatError,
  filteredChatList,
  selectedChatId,
  onSelectChat,
  onDeleteChat,
  busy,
}) {
  return (
    <section style={panelStyle} data-testid="chat-config-list-panel">
      <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' }}>
          <div style={{ fontSize: '1rem', fontWeight: 950, color: '#111827' }}>对话</div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{chatLoading ? '加载中...' : `${chatListLength} 个`}</div>
            {isAdmin ? (
              <button
                type="button"
                onClick={onOpenCreate}
                data-testid="chat-config-new"
                style={{
                  padding: '6px 10px',
                  borderRadius: '10px',
                  border: '1px solid #1d4ed8',
                  background: '#1d4ed8',
                  color: '#ffffff',
                  cursor: 'pointer',
                  fontWeight: 900,
                }}
              >
                新建
              </button>
            ) : null}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
          <input
            value={chatFilter}
            onChange={(event) => onFilterChange && onFilterChange(event.target.value)}
            data-testid="chat-config-filter"
            placeholder="按名称/编号/描述筛选"
            style={{ flex: 1, padding: '10px 12px', border: '1px solid #e5e7eb', borderRadius: '10px', outline: 'none' }}
          />
          <button
            type="button"
            onClick={onRefresh}
            disabled={chatLoading}
            data-testid="chat-config-refresh"
            style={{
              padding: '10px 12px',
              borderRadius: '10px',
              border: '1px solid #e5e7eb',
              background: chatLoading ? '#f3f4f6' : '#ffffff',
              cursor: chatLoading ? 'not-allowed' : 'pointer',
              fontWeight: 800,
            }}
          >
            刷新
          </button>
        </div>

        {chatError ? (
          <div data-testid="chat-config-list-error" style={{ marginTop: '10px', color: '#b91c1c', fontSize: '0.9rem' }}>
            {chatError}
          </div>
        ) : null}
      </div>

      <div style={{ padding: '12px' }}>
        {filteredChatList.map((chat) => {
          const id = String(chat?.id || '');
          const name = String(chat?.name || '');
          const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_');
          const isSelected = String(selectedChatId || '') === id;
          const deleteDisabled = !isAdmin || busy;

          return (
            <div key={id} style={{ position: 'relative', marginBottom: '10px' }}>
              <button
                type="button"
                onClick={() => onSelectChat && onSelectChat(id)}
                data-testid={`chat-config-item-${safeId}`}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 56px 12px 12px',
                  borderRadius: '10px',
                  border: `1px solid ${isSelected ? '#60a5fa' : '#e5e7eb'}`,
                  background: isSelected ? '#eff6ff' : '#ffffff',
                  cursor: 'pointer',
                }}
                title={id}
              >
                <div style={{ fontWeight: 950, color: '#111827', fontSize: '0.95rem', lineHeight: 1.2 }}>{name || '(未命名)'}</div>
                <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.8rem' }}>{id ? `编号：${id}` : '编号：（未知）'}</div>
              </button>

              {isAdmin ? (
                <button
                  type="button"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onDeleteChat && onDeleteChat({ ...chat, id });
                  }}
                  disabled={deleteDisabled}
                  data-testid={`chat-config-delete-${safeId}`}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    top: '10px',
                    width: '44px',
                    height: '36px',
                    borderRadius: '10px',
                    border: `1px solid ${deleteDisabled ? '#e5e7eb' : '#fecaca'}`,
                    background: deleteDisabled ? '#f9fafb' : '#fff1f2',
                    color: deleteDisabled ? '#9ca3af' : '#b91c1c',
                    cursor: deleteDisabled ? 'not-allowed' : 'pointer',
                    fontWeight: 900,
                  }}
                >
                  删除
                </button>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
