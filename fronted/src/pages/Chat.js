import React, { useCallback, useEffect, useRef, useState } from 'react';
import { httpClient } from '../shared/http/httpClient';
import { chatApi } from '../features/chat/api';

const Chat = () => {
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, sessionId: null, sessionName: '' });

  const messagesEndRef = useRef(null);
  const assistantMessageRef = useRef('');

  const upsertAssistantMessage = useCallback((content) => {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === 'assistant') {
        next[next.length - 1] = { role: 'assistant', content };
      }
      return next;
    });
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchChats = async () => {
    try {
      setLoading(true);
      const data = await chatApi.listMyChats();
      const list = data.chats || [];
      setChats(list);
      if (list.length > 0) {
        setSelectedChatId(list[0].id);
      } else {
        setSelectedChatId(null);
      }
    } catch (err) {
      setError(err.message || '加载聊天助手失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchSessions = async (chatId) => {
    if (!chatId) return;
    try {
      const data = await chatApi.listChatSessions(chatId);
      const list = data.sessions || [];
      setSessions(list);
      if (list.length > 0) {
        setSelectedSessionId(list[0].id);
        setMessages(list[0].messages || []);
      } else {
        setSelectedSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message || '加载会话失败');
    }
  };

  useEffect(() => {
    fetchChats();
  }, []);

  useEffect(() => {
    if (selectedChatId) {
      fetchSessions(selectedChatId);
    } else {
      setSessions([]);
      setSelectedSessionId(null);
      setMessages([]);
    }
  }, [selectedChatId]);

  const createSession = async () => {
    if (!selectedChatId) return;
    try {
      const session = await chatApi.createChatSession(selectedChatId, '新会话');
      setSessions((prev) => [session, ...prev]);
      setSelectedSessionId(session.id);
      setMessages(session.messages || []);
    } catch (err) {
      setError(err.message || '新建会话失败');
    }
  };

  const selectSession = (sessionId) => {
    const session = sessions.find((s) => s.id === sessionId);
    if (!session) return;
    setSelectedSessionId(sessionId);
    setMessages(session.messages || []);
  };

  const confirmDeleteSession = async () => {
    if (!deleteConfirm.sessionId || !selectedChatId) return;
    try {
      await chatApi.deleteChatSessions(selectedChatId, [deleteConfirm.sessionId]);
      setSessions((prev) => prev.filter((s) => s.id !== deleteConfirm.sessionId));
      if (selectedSessionId === deleteConfirm.sessionId) {
        setSelectedSessionId(null);
        setMessages([]);
      }
      setDeleteConfirm({ show: false, sessionId: null, sessionName: '' });
    } catch (err) {
      setError(err.message || '删除会话失败');
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !selectedChatId) return;
    const question = inputMessage.trim();
    const userMessage = { role: 'user', content: question };

    setMessages((prev) => [...prev, userMessage, { role: 'assistant', content: '' }]);
    setInputMessage('');
    setError(null);

    try {
      const response = await httpClient.request(`/api/chats/${selectedChatId}/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, stream: true, session_id: selectedSessionId }),
      });

      if (!response.ok) {
        throw new Error('发送消息失败');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      assistantMessageRef.current = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.slice(6).trim();
          if (!dataStr || dataStr === '[DONE]') continue;

          try {
            const data = JSON.parse(dataStr);
            if (data.code === 0 && data.data && data.data.answer) {
              assistantMessageRef.current += data.data.answer;
              upsertAssistantMessage(assistantMessageRef.current);
            }
          } catch {
            // ignore malformed SSE chunks
          }
        }
      }
    } catch (err) {
      setError(err.message || '发送失败');
      // remove placeholder assistant message
      setMessages((prev) => prev.slice(0, -1));
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{ height: 'calc(100vh - 120px)', display: 'flex', gap: '16px' }}>
      <div style={{ width: '320px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div
          style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '16px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            maxHeight: '300px',
            overflowY: 'auto',
          }}
        >
          <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem' }}>聊天助手</h3>
          {loading ? (
            <div style={{ color: '#6b7280', textAlign: 'center', padding: '20px' }}>加载中...</div>
          ) : chats.length === 0 ? (
            <div style={{ color: '#6b7280', textAlign: 'center', padding: '20px' }}>暂无可用聊天助手</div>
          ) : (
            chats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => setSelectedChatId(chat.id)}
                style={{
                  padding: '8px 12px',
                  marginBottom: '8px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  backgroundColor: selectedChatId === chat.id ? '#3b82f6' : '#f3f4f6',
                  color: selectedChatId === chat.id ? 'white' : '#1f2937',
                }}
              >
                {chat.name || chat.id}
              </div>
            ))
          )}
        </div>

        <div
          style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '16px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            flex: 1,
            overflowY: 'auto',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '1rem' }}>会话</h3>
            <button
              onClick={createSession}
              disabled={!selectedChatId}
              style={{
                padding: '6px 10px',
                borderRadius: '4px',
                border: 'none',
                cursor: selectedChatId ? 'pointer' : 'not-allowed',
                backgroundColor: selectedChatId ? '#3b82f6' : '#9ca3af',
                color: 'white',
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
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 10px',
                  marginBottom: '8px',
                  borderRadius: '6px',
                  backgroundColor: selectedSessionId === s.id ? '#eef2ff' : '#f9fafb',
                  border: selectedSessionId === s.id ? '1px solid #c7d2fe' : '1px solid #e5e7eb',
                  cursor: 'pointer',
                  gap: '8px',
                }}
                onClick={() => selectSession(s.id)}
              >
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  {s.name || s.id}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteConfirm({ show: true, sessionId: s.id, sessionName: s.name || s.id });
                  }}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: '#ef4444',
                    color: 'white',
                    cursor: 'pointer',
                  }}
                >
                  删除
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', fontWeight: 600 }}>
          {selectedChatId ? '对话' : '请选择聊天助手开始对话'}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
          {messages.length === 0 ? (
            <div style={{ color: '#6b7280' }}>开始新的对话...</div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  marginBottom: '12px',
                  display: 'flex',
                  justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '75%',
                    padding: '10px 12px',
                    borderRadius: '10px',
                    backgroundColor: m.role === 'user' ? '#3b82f6' : '#f3f4f6',
                    color: m.role === 'user' ? 'white' : '#111827',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {m.content}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div style={{ padding: '10px 16px', backgroundColor: '#fee2e2', color: '#991b1b' }}>{error}</div>
        )}

        <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '10px' }}>
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyPress}
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
            disabled={!selectedChatId}
          />
          <button
            onClick={sendMessage}
            disabled={!selectedChatId || !inputMessage.trim()}
            style={{
              padding: '0 16px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: !selectedChatId || !inputMessage.trim() ? '#9ca3af' : '#3b82f6',
              color: 'white',
              cursor: !selectedChatId || !inputMessage.trim() ? 'not-allowed' : 'pointer',
              fontWeight: 600,
            }}
          >
            发送
          </button>
        </div>
      </div>

      {deleteConfirm.show && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000,
          }}
        >
          <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', width: '100%', maxWidth: '420px' }}>
            <h3 style={{ margin: '0 0 12px 0' }}>确认删除会话</h3>
            <div style={{ color: '#374151', marginBottom: '16px' }}>
              确定要删除会话“<strong>{deleteConfirm.sessionName}</strong>”吗？
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={() => setDeleteConfirm({ show: false, sessionId: null, sessionName: '' })}
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                取消
              </button>
              <button
                onClick={confirmDeleteSession}
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat;
