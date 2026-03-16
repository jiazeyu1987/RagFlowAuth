import React from 'react';

export default function ChatConfigListPanel({
  panelClassName,
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
    <section className={panelClassName} data-testid="chat-config-list-panel">
      <div className="admin-med-panel__head">
        <div className="admin-med-head" style={{ alignItems: 'baseline' }}>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: '#163f63' }}>对话列表</div>
          <div className="admin-med-inline-note">{chatLoading ? '加载中...' : `共 ${chatListLength} 项`}</div>
        </div>

        <div className="admin-med-actions" style={{ marginTop: 10 }}>
          <input
            value={chatFilter}
            onChange={(event) => onFilterChange && onFilterChange(event.target.value)}
            data-testid="chat-config-filter"
            placeholder="按名称、编号或描述筛选"
            className="medui-input"
            style={{ flex: 1, minWidth: 180 }}
          />
          <button type="button" onClick={onRefresh} disabled={chatLoading} data-testid="chat-config-refresh" className="medui-btn medui-btn--secondary">
            刷新
          </button>
          {isAdmin ? (
            <button type="button" onClick={onOpenCreate} data-testid="chat-config-new" className="medui-btn medui-btn--primary">
              新建对话
            </button>
          ) : null}
        </div>
      </div>

      <div className="admin-med-panel__body admin-med-list-scroll">
        {chatError ? <div data-testid="chat-config-list-error" className="admin-med-danger">{chatError}</div> : null}

        {filteredChatList.length === 0 ? (
          <div className="medui-empty" style={{ paddingTop: 16 }}>暂无可显示对话</div>
        ) : (
          filteredChatList.map((chat) => {
            const id = String(chat?.id || '');
            const name = String(chat?.name || '');
            const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_');
            const isSelected = String(selectedChatId || '') === id;
            const deleteDisabled = !isAdmin || busy;

            return (
              <div key={id} className="admin-med-list-item">
                <button
                  type="button"
                  onClick={() => onSelectChat && onSelectChat(id)}
                  data-testid={`chat-config-item-${safeId}`}
                  className={`admin-med-list-item__button${isSelected ? ' is-active' : ''}`}
                >
                  <div className="admin-med-list-item__title">{name || '（未命名）'}</div>
                  <div className="admin-med-list-item__meta">{id ? `编号：${id}` : '编号：（未知）'}</div>
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
                    className="medui-btn medui-btn--danger admin-med-list-item__delete"
                    title="删除"
                  >
                    删除
                  </button>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
