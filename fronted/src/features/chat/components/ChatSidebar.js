import React from 'react';

const normalizeSessionDisplayName = (session) => {
  const raw = String(session?.name || '').trim();
  if (!raw) return String(session?.id || '');
  const lowered = raw.toLowerCase();
  if (lowered === 'new chat' || lowered === 'new session') return '新对话';
  return raw;
};

export default function ChatSidebar({
  loading,
  chats,
  selectedChatId,
  sessions,
  selectedSessionId,
  onSelectChat,
  onCreateSession,
  onSelectSession,
  onOpenRenameDialog,
  onOpenDeleteDialog,
}) {
  return (
    <div className="chat-med-sidebar">
      <div data-testid="chat-list" className="chat-med-card">
        <div className="chat-med-card__head">
          <div className="chat-med-card__title">智能助手</div>
        </div>
        <div className="chat-med-card__body medui-scroll" style={{ maxHeight: 320 }}>
          {loading ? (
            <div className="medui-empty">加载中...</div>
          ) : chats.length === 0 ? (
            <div className="medui-empty">暂无可用助手</div>
          ) : (
            <div className="chat-med-list">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  data-testid={`chat-item-${chat.id}`}
                  onClick={() => onSelectChat(chat.id)}
                  className={`chat-med-item ${selectedChatId === chat.id ? 'is-active' : ''}`}
                  role="button"
                  tabIndex={0}
                >
                  <div className="chat-med-item__name">{chat.name || chat.id}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div data-testid="chat-sessions" className="chat-med-card" style={{ flex: 1, minHeight: 0 }}>
        <div className="chat-med-card__head">
          <div className="medui-header-row">
            <div className="chat-med-card__title">会话管理</div>
            <button
              onClick={onCreateSession}
              disabled={!selectedChatId}
              data-testid="chat-session-create"
              type="button"
              className="medui-btn medui-btn--primary"
            >
              新建会话
            </button>
          </div>
        </div>
        <div className="chat-med-card__body medui-scroll" style={{ height: '100%' }}>
          {!selectedChatId ? (
            <div className="medui-empty">请先选择助手</div>
          ) : sessions.length === 0 ? (
            <div className="medui-empty">暂无会话，请点击“新建会话”开始。</div>
          ) : (
            <div className="chat-med-list">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  data-testid={`chat-session-item-${session.id}`}
                  className={`chat-med-item ${selectedSessionId === session.id ? 'is-active' : ''}`}
                  onClick={() => onSelectSession(session.id)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="medui-header-row" style={{ alignItems: 'center' }}>
                    <div className="chat-med-item__name" style={{ flex: 1 }}>
                      {normalizeSessionDisplayName(session)}
                    </div>
                    <div className="chat-med-item__actions">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpenRenameDialog(session);
                        }}
                        data-testid={`chat-session-rename-${session.id}`}
                        className="medui-btn medui-btn--secondary"
                        style={{ height: 30, padding: '0 10px', fontSize: '0.78rem' }}
                      >
                        重命名
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpenDeleteDialog(session);
                        }}
                        data-testid={`chat-session-delete-${session.id}`}
                        className="medui-btn medui-btn--danger"
                        style={{ height: 30, padding: '0 10px', fontSize: '0.78rem' }}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
