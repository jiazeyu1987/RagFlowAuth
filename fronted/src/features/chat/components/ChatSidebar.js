import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

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
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const cardStyle = {
    backgroundColor: 'white',
    borderRadius: isMobile ? '12px' : '8px',
    padding: isMobile ? '14px' : '16px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  };

  return (
    <div style={{ width: isMobile ? '100%' : '320px', display: 'flex', flexDirection: 'column', gap: isMobile ? '12px' : '16px', flexShrink: 0 }}>
      <div
        data-testid="chat-list"
        style={{
          ...cardStyle,
          maxHeight: isMobile ? 'none' : '300px',
          overflowY: 'auto',
        }}
      >
        <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem' }}>聊天助手</h3>
        {loading ? (
          <div style={{ color: '#6b7280', textAlign: 'center', padding: '20px' }}>加载中...</div>
        ) : chats.length === 0 ? (
          <div style={{ color: '#6b7280', textAlign: 'center', padding: '20px' }}>暂无可用聊天助手</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: isMobile ? 'row' : 'column', gap: '8px', flexWrap: 'wrap' }}>
            {chats.map((chat) => (
              <div
                key={chat.id}
                data-testid={`chat-item-${chat.id}`}
                onClick={() => onSelectChat(chat.id)}
                style={{
                  padding: isMobile ? '10px 12px' : '8px 12px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  backgroundColor: selectedChatId === chat.id ? '#3b82f6' : '#f3f4f6',
                  color: selectedChatId === chat.id ? 'white' : '#1f2937',
                  flex: isMobile ? '1 1 140px' : 'unset',
                  minWidth: 0,
                  wordBreak: 'break-word',
                }}
              >
                {chat.name || chat.id}
              </div>
            ))}
          </div>
        )}
      </div>

      <div
        data-testid="chat-sessions"
        style={{
          ...cardStyle,
          flex: 1,
          overflowY: 'auto',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', gap: '12px' }}>
          <h3 style={{ margin: 0, fontSize: '1rem' }}>会话</h3>
          <button
            onClick={onCreateSession}
            disabled={!selectedChatId}
            data-testid="chat-session-create"
            style={{
              padding: '7px 12px',
              borderRadius: '8px',
              border: 'none',
              cursor: selectedChatId ? 'pointer' : 'not-allowed',
              backgroundColor: selectedChatId ? '#3b82f6' : '#9ca3af',
              color: 'white',
              whiteSpace: 'nowrap',
            }}
          >
            新建
          </button>
        </div>

        {!selectedChatId ? (
          <div style={{ color: '#6b7280', padding: '12px 0' }}>请先选择聊天助手</div>
        ) : sessions.length === 0 ? (
          <div style={{ color: '#6b7280', padding: '12px 0' }}>暂无会话，请点击“新建”</div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              data-testid={`chat-session-item-${s.id}`}
              style={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                justifyContent: 'space-between',
                alignItems: isMobile ? 'stretch' : 'center',
                padding: isMobile ? '10px 12px' : '8px 10px',
                marginBottom: '8px',
                borderRadius: '10px',
                backgroundColor: selectedSessionId === s.id ? '#eef2ff' : '#f9fafb',
                border: selectedSessionId === s.id ? '1px solid #c7d2fe' : '1px solid #e5e7eb',
                cursor: 'pointer',
                gap: '10px',
              }}
              onClick={() => onSelectSession(s.id)}
            >
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: isMobile ? 'normal' : 'nowrap', flex: 1, wordBreak: 'break-word' }}>
                {s.name || s.id}
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: isMobile ? 'flex-end' : 'flex-start', flexWrap: 'wrap' }}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenRenameDialog(s);
                  }}
                  data-testid={`chat-session-rename-${s.id}`}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: '#6b7280',
                    color: 'white',
                    cursor: 'pointer',
                  }}
                >
                  重命名
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenDeleteDialog(s);
                  }}
                  data-testid={`chat-session-delete-${s.id}`}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: '#ef4444',
                    color: 'white',
                    cursor: 'pointer',
                  }}
                >
                  删除
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
