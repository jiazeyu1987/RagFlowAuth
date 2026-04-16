import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

export default function ChatComposer({
  selectedChatId,
  selectedSessionId,
  inputMessage,
  setInputMessage,
  onKeyPress,
  onCreateSession,
  onSendMessage,
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

  if (!selectedChatId) {
    return (
      <div style={{ padding: isMobile ? '12px' : '12px', borderTop: '1px solid #e5e7eb', color: '#6b7280' }}>
        请先选择聊天助手
      </div>
    );
  }

  if (!selectedSessionId) {
    return (
      <div style={{ padding: isMobile ? '12px' : '12px', borderTop: '1px solid #e5e7eb' }}>
        <button
          onClick={onCreateSession}
          data-testid="chat-create-session-bottom"
          style={{
            width: isMobile ? '100%' : 'auto',
            padding: '10px 14px',
            borderRadius: '10px',
            border: 'none',
            backgroundColor: '#3b82f6',
            color: 'white',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          新建会话
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: isMobile ? '10px 12px 12px' : '12px',
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        gap: '10px',
      }}
    >
      <textarea
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={onKeyPress}
        data-testid="chat-input"
        placeholder="输入消息（回车发送，使用组合键换行）"
        style={{
          flex: 1,
          width: '100%',
          resize: 'none',
          padding: isMobile ? '11px 12px' : '10px 12px',
          borderRadius: '10px',
          border: '1px solid #d1d5db',
          outline: 'none',
          minHeight: isMobile ? '84px' : '44px',
          maxHeight: isMobile ? '160px' : '120px',
          boxSizing: 'border-box',
          fontSize: '0.95rem',
          lineHeight: 1.5,
        }}
      />
      <button
        onClick={onSendMessage}
        disabled={!inputMessage.trim()}
        data-testid="chat-send"
        style={{
          width: isMobile ? '100%' : 'auto',
          minHeight: isMobile ? '44px' : 'auto',
          padding: isMobile ? '12px 16px' : '0 16px',
          borderRadius: '10px',
          border: 'none',
          backgroundColor: !inputMessage.trim() ? '#9ca3af' : '#3b82f6',
          color: 'white',
          cursor: !inputMessage.trim() ? 'not-allowed' : 'pointer',
          fontWeight: 600,
          flexShrink: 0,
        }}
      >
        发送
      </button>
    </div>
  );
}
