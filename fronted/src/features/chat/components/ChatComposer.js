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
    return <div className="chat-med-composer__hint">请先选择助手。</div>;
  }

  if (!selectedSessionId) {
    return (
      <div className="chat-med-composer__hint">
        <button
          onClick={onCreateSession}
          data-testid="chat-create-session-bottom"
          type="button"
          className="medui-btn medui-btn--primary"
        >
          新建会话
        </button>
      </div>
    );
  }

  return (
    <div className="chat-med-composer">
      <textarea
        value={inputMessage}
        onChange={(event) => setInputMessage(event.target.value)}
        onKeyDown={onKeyPress}
        data-testid="chat-input"
        placeholder="请输入消息。回车发送，使用换行组合键可换行。"
        className="medui-textarea"
        style={{ flex: 1, resize: 'none', maxHeight: 140 }}
      />
      <button
        onClick={onSendMessage}
        disabled={!inputMessage.trim()}
        data-testid="chat-send"
        type="button"
        className="medui-btn medui-btn--primary"
        style={{ minWidth: 88, height: 42 }}
      >
        发送
      </button>
    </div>
  );
}
