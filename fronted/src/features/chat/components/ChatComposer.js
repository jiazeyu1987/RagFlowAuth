import React from 'react';

export default function ChatComposer({
  selectedChatId,
  selectedSessionId,
  inputMessage,
  setInputMessage,
  onKeyPress,
  onCreateSession,
  onSendMessage,
}) {
  if (!selectedChatId) {
    return (
      <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb', color: '#6b7280' }}>
        请先选择聊天助手
      </div>
    );
  }

  if (!selectedSessionId) {
    return (
      <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb' }}>
        <button
          onClick={onCreateSession}
          data-testid="chat-create-session-bottom"
          style={{
            padding: '10px 14px',
            borderRadius: '6px',
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
    <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '10px' }}>
      <textarea
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={onKeyPress}
        data-testid="chat-input"
        placeholder="输入消息...（Enter 发送，Shift+Enter 换行）"
        style={{
          flex: 1,
          resize: 'none',
          padding: '10px 12px',
          borderRadius: '6px',
          border: '1px solid #d1d5db',
          outline: 'none',
          minHeight: '44px',
          maxHeight: '120px',
        }}
      />
      <button
        onClick={onSendMessage}
        disabled={!inputMessage.trim()}
        data-testid="chat-send"
        style={{
          padding: '0 16px',
          borderRadius: '6px',
          border: 'none',
          backgroundColor: !inputMessage.trim() ? '#9ca3af' : '#3b82f6',
          color: 'white',
          cursor: !inputMessage.trim() ? 'not-allowed' : 'pointer',
          fontWeight: 600,
        }}
      >
        发送
      </button>
    </div>
  );
}
