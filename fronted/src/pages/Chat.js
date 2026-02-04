import React, { useCallback, useEffect, useRef, useState } from 'react';
import { httpClient } from '../shared/http/httpClient';
import { chatApi } from '../features/chat/api';
import ReactMarkdown from 'react-markdown';

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
  const [renameDialog, setRenameDialog] = useState({ show: false, sessionId: null, value: '' });
  const [previewDialog, setPreviewDialog] = useState({ show: false, title: '', loading: false, error: '', payload: null });
  const [citationHover, setCitationHover] = useState(null);

  const messagesEndRef = useRef(null);
  const assistantMessageRef = useRef('');
  const assistantSourcesRef = useRef([]);

  const normalizeForCompare = useCallback((value) => {
    return String(value ?? '')
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .split('\u0000')
      .join('');
  }, []);

  const stripThinkTags = useCallback((value) => {
    const text = String(value ?? '');
    if (!text) return '';

    // Remove <think>...</think> blocks (including multiline).
    let out = text.replace(/<think>[\s\S]*?<\/think>/g, '');
    // If streaming ended mid-think, hide the unfinished tail.
    out = out.replace(/<think>[\s\S]*$/g, '');
    return out;
  }, []);

  const extractCitationIds = useCallback((value) => {
    const text = String(value ?? '');
    const ids = new Set();
    const re = /\[ID:(\d+)\]/g;
    let match = null;
    while ((match = re.exec(text)) !== null) {
      const n = Number(match[1]);
      if (!Number.isNaN(n)) ids.add(n);
    }
    return Array.from(ids).sort((a, b) => a - b);
  }, []);

  const normalizeThinkForDisplay = useCallback((value) => {
    const text = String(value ?? '');
    if (!text) return '';

    // Streaming may produce "growing prefix" repetitions:
    // line1, line1+more, line1+more+more...
    // Collapse by removing lines that are prefixes of any later line.
    const rawLines = text
      .split('\n')
      .map((l) => String(l ?? '').replace(/\r/g, ''))
      .map((l) => l.trim())
      .filter(Boolean);
    if (rawLines.length <= 1) return rawLines[0] || '';

    const norm = (s) =>
      String(s ?? '')
        .trim()
        .replace(/\s+/g, ' ')
        .replace(/[“”]/g, '"')
        .replace(/[‘’]/g, "'");

    const normLines = rawLines.map(norm);

    const keep = new Array(rawLines.length).fill(true);
    for (let i = 0; i < rawLines.length; i++) {
      const li = normLines[i];
      for (let j = i + 1; j < rawLines.length; j++) {
        const lj = normLines[j];
        if (!li) continue;
        if (lj.length >= li.length && (lj === li || lj.startsWith(li))) {
          keep[i] = false;
          break;
        }
      }
    }

    const out = rawLines.filter((_, idx) => keep[idx]);

    // If it's clearly a cumulative chain, prefer showing only the last line for readability.
    const keptCount = out.length;
    if (rawLines.length >= 3 && keptCount === 1) return out[0];

    // Dedupe exact repeats (after whitespace normalization)
    const seen = new Set();
    const deduped = [];
    for (const line of out) {
      const key = norm(line);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      deduped.push(line);
    }

    return deduped.join('\n');
  }, []);

  const normalizeSource = useCallback((src) => {
    const s = src && typeof src === 'object' ? src : {};
    const docId =
      s.doc_id || s.docId || s.document_id || s.documentId || s.ragflow_doc_id || s.ragflowDocId || s.id || '';
    const dataset =
      s.dataset_id ||
      s.datasetId ||
      s.dataset ||
      s.dataset_name ||
      s.datasetName ||
      s.kb_id ||
      s.kbId ||
      s.kb_name ||
      s.kbName ||
      '';
    const title =
      s.filename ||
      s.doc_name ||
      s.docName ||
      s.document_name ||
      s.documentName ||
      s.name ||
      s.title ||
      docId ||
      'unknown';
    const chunk = s.chunk || s.chunk_text || s.chunkText || s.content || s.text || '';
    return {
      docId: String(docId || ''),
      dataset: String(dataset || ''),
      title: String(title || ''),
      chunk: String(chunk || ''),
    };
  }, []);

  const debugChatCitations = useCallback(() => {
    try {
      return String(window?.localStorage?.getItem('RAGFLOWAUTH_DEBUG_CHAT_CITATIONS') || '') === '1';
    } catch {
      return false;
    }
  }, []);

  const debugLogCitations = useCallback(
    (...args) => {
      if (!debugChatCitations()) return;
      // eslint-disable-next-line no-console
      console.debug('[Chat:Citations]', ...args);
    },
    [debugChatCitations]
  );

  const rewriteCitationLinks = useCallback((text) => {
    const input = String(text ?? '');
    // Turn "[ID:6]" into a safe in-page anchor so ReactMarkdown doesn't sanitize it away.
    // We'll render "#cid-6" as a custom hover-only control via the <a> component.
    return input.replace(/\[ID:(\d+)\]/g, (_m, id) => `[ID:${id}](#cid-${id})`);
  }, []);

  const onCitationClick = useCallback((e, { id, chunk }) => {
    const rect = e?.currentTarget?.getBoundingClientRect?.();
    const x = rect ? rect.left + rect.width / 2 : (e?.clientX ?? 0);
    const y = rect ? rect.top : (e?.clientY ?? 0);
    // eslint-disable-next-line no-console
    console.debug('[Chat:CitationPopup] open', { id, chunkLen: String(chunk || '').length, x, y });
    setCitationHover({
      id,
      chunk: String(chunk || '').trim() || '(未获取到chunk内容)',
      x,
      y,
    });
  }, []);

  const onCitationPopupLeave = useCallback(() => {
    // eslint-disable-next-line no-console
    console.debug('[Chat:CitationPopup] close');
    setCitationHover(null);
  }, []);

  const computeMessageKey = useCallback((chatId, sessionId, content) => {
    const text = String(content ?? '');
    // Simple stable hash (djb2)
    let hash = 5381;
    for (let i = 0; i < text.length; i++) {
      hash = ((hash << 5) + hash) ^ text.charCodeAt(i);
      hash >>>= 0;
    }
    return `ragflowauth_chat_sources_v1:${String(chatId || '')}:${String(sessionId || '')}:${hash.toString(16)}`;
  }, []);

  const saveSourcesForAssistantMessage = useCallback(
    (chatId, sessionId, content, sources) => {
      const list = Array.isArray(sources) ? sources : [];
      if (!chatId || !sessionId || !content || list.length === 0) return;
      try {
        const key = computeMessageKey(chatId, sessionId, content);
        window.localStorage.setItem(key, JSON.stringify(list));
        debugLogCitations('persist sources', { key, count: list.length });
      } catch (e) {
        debugLogCitations('persist sources failed', { error: e?.message || String(e || '') });
      }
    },
    [computeMessageKey, debugLogCitations]
  );

  const loadSourcesForAssistantMessage = useCallback(
    (chatId, sessionId, content) => {
      if (!chatId || !sessionId || !content) return null;
      try {
        const key = computeMessageKey(chatId, sessionId, content);
        const raw = window.localStorage.getItem(key);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : null;
      } catch {
        return null;
      }
    },
    [computeMessageKey]
  );

  const restoreSourcesIntoMessages = useCallback(
    (chatId, sessionId, messageList) => {
      const msgs = Array.isArray(messageList) ? messageList : [];
      return msgs.map((m) => {
        if (!m || typeof m !== 'object') return m;
        if (m.role !== 'assistant') return m;
        const content = stripThinkTags(m.content);
        const existing = Array.isArray(m.sources) ? m.sources : [];
        if (existing.length > 0) return m;
        const restored = loadSourcesForAssistantMessage(chatId, sessionId, content);
        if (Array.isArray(restored) && restored.length > 0) {
          return { ...m, sources: restored };
        }
        return m;
      });
    },
    [loadSourcesForAssistantMessage, stripThinkTags]
  );

  const upsertAssistantMessage = useCallback((content) => {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === 'assistant') {
        next[next.length - 1] = { ...last, role: 'assistant', content };
      }
      return next;
    });
  }, []);

  const markAssistantMessageFinal = useCallback(() => {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === 'assistant') {
        next[next.length - 1] = { ...last, role: 'assistant', isFinal: true };
      }
      return next;
    });
  }, []);

  const upsertAssistantSources = useCallback((sources) => {
    const list = Array.isArray(sources) ? sources : [];
    assistantSourcesRef.current = list;
    try {
      debugLogCitations(
        'sources received',
        list.map((s) => {
          const n = normalizeSource(s);
          return {
            raw_title: s?.filename || s?.title || s?.name || '',
            normalized_title: n.title,
            docId: n.docId,
            dataset: n.dataset,
          };
        })
      );
    } catch {
      // ignore
    }
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === 'assistant') {
        next[next.length - 1] = { ...last, role: 'assistant', sources: list };
      }
      return next;
    });
  }, [debugLogCitations, normalizeSource]);

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
        setMessages(restoreSourcesIntoMessages(chatId, list[0].id, list[0].messages || []));
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
      const selectedChat = chats.find((c) => c.id === selectedChatId);
      const chatName = String(selectedChat?.name || '').trim();
      const sessionName = chatName || '新会话';

      const session = await chatApi.createChatSession(selectedChatId, sessionName);
      setSessions((prev) => [session, ...prev]);
      setSelectedSessionId(session.id);
      setMessages(restoreSourcesIntoMessages(selectedChatId, session.id, session.messages || []));
    } catch (err) {
      setError(err.message || '新建会话失败');
    }
  };

  const selectSession = (sessionId) => {
    const session = sessions.find((s) => s.id === sessionId);
    if (!session) return;
    setSelectedSessionId(sessionId);
    setMessages(restoreSourcesIntoMessages(selectedChatId, sessionId, session.messages || []));
  };

  const confirmDeleteSession = async () => {
    if (!deleteConfirm.sessionId || !selectedChatId) return;
    try {
      await chatApi.deleteChatSessions(selectedChatId, [deleteConfirm.sessionId]);
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.id !== deleteConfirm.sessionId);
        if (selectedSessionId === deleteConfirm.sessionId) {
          if (remaining.length > 0) {
            setSelectedSessionId(remaining[0].id);
            setMessages(restoreSourcesIntoMessages(selectedChatId, remaining[0].id, remaining[0].messages || []));
          } else {
            setSelectedSessionId(null);
            setMessages([]);
          }
        }
        return remaining;
      });
      setDeleteConfirm({ show: false, sessionId: null, sessionName: '' });
    } catch (err) {
      setError(err.message || '删除会话失败');
    }
  };

  const confirmRenameSession = async () => {
    if (!renameDialog.sessionId || !selectedChatId) return;
    const newName = String(renameDialog.value || '').trim();
    if (!newName) return;
    try {
      await chatApi.renameChatSession(selectedChatId, renameDialog.sessionId, newName);
      setSessions((prev) => prev.map((s) => (s.id === renameDialog.sessionId ? { ...s, name: newName } : s)));
      setRenameDialog({ show: false, sessionId: null, value: '' });
    } catch (err) {
      setError(err.message || '重命名失败');
    }
  };

  const openSourcePreview = useCallback(
    async (rawSource) => {
      const source = normalizeSource(rawSource);
      if (!source.docId || !source.dataset) return;
      debugLogCitations('download GET start', { before_title: source.title, docId: source.docId, dataset: source.dataset });
      debugLogCitations('preview GET start', { before_title: source.title, docId: source.docId, dataset: source.dataset });
      setPreviewDialog({ show: true, title: source.title, loading: true, error: '', payload: null });
      try {
        const qs = new URLSearchParams({ dataset: source.dataset }).toString();
        const data = await httpClient.requestJson(`/api/ragflow/documents/${encodeURIComponent(source.docId)}/preview?${qs}`);
        debugLogCitations('preview GET done', { before_title: source.title, after_title: data?.filename || '', type: data?.type || '' });
        setPreviewDialog({ show: true, title: data?.filename || source.title, loading: false, error: '', payload: data });
      } catch (e) {
        debugLogCitations('preview GET fail', { before_title: source.title, error: e?.message || String(e || '') });
        setPreviewDialog({ show: true, title: source.title, loading: false, error: e?.message || '预览失败', payload: null });
      }
    },
    [debugLogCitations, normalizeSource]
  );

  const downloadSource = useCallback(
    async (rawSource) => {
      const source = normalizeSource(rawSource);
      if (!source.docId || !source.dataset) return;
      const qs = new URLSearchParams({ dataset: source.dataset, filename: source.title }).toString();
      const res = await httpClient.request(`/api/ragflow/documents/${encodeURIComponent(source.docId)}/download?${qs}`, { method: 'GET' });
      if (!res.ok) {
        let message = `下载失败 (${res.status})`;
        try {
          const data = await res.json();
          message = data?.detail || data?.message || message;
        } catch {
          // ignore
        }
        throw new Error(message);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      try {
        const a = document.createElement('a');
        a.href = url;
        a.download = source.title || `document_${source.docId}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } finally {
        URL.revokeObjectURL(url);
      }
    },
    [debugLogCitations, normalizeSource]
  );

  const sendMessage = async () => {
    if (!inputMessage.trim() || !selectedChatId || !selectedSessionId) return;
    const question = inputMessage.trim();
    const userMessage = { role: 'user', content: question };

    setMessages((prev) => [...prev, userMessage, { role: 'assistant', content: '', sources: [] }]);
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
      assistantSourcesRef.current = [];

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
            if (data?.code === 0 && data?.data && Array.isArray(data.data.sources)) {
              upsertAssistantSources(data.data.sources);
            }
            if (data.code === 0 && data.data && data.data.answer) {
              const incoming = String(data.data.answer ?? '');
              if (!incoming) continue;

              // RAGFlow streaming payloads may be either:
              // - delta chunks (append-only), or
              // - full text so far (cumulative), or
              // - overlapping chunks (some already-sent prefix repeated).
              // Handle all to avoid duplicating content in the UI.
              const current = assistantMessageRef.current || '';
              const currentNorm = normalizeForCompare(current);
              const incomingNorm = normalizeForCompare(incoming);
              let next = '';

              // Heuristic: treat as "cumulative so far" when the incoming text shares a very long common prefix
              // with what we already have, even if it doesn't strictly startWith due to minor formatting changes.
              if (currentNorm && incomingNorm && incomingNorm.length > currentNorm.length) {
                let prefixLen = 0;
                const max = Math.min(currentNorm.length, incomingNorm.length);
                for (let k = 0; k < max; k++) {
                  if (currentNorm[k] !== incomingNorm[k]) break;
                  prefixLen++;
                }
                const ratio = prefixLen / Math.max(1, currentNorm.length);
                if (ratio >= 0.8 || prefixLen >= 400) {
                  next = incoming;
                }
              }
              if (next) {
                assistantMessageRef.current = next;
                upsertAssistantMessage(stripThinkTags(next));
                continue;
              }
              if (incomingNorm === currentNorm) {
                next = current;
              } else if (incomingNorm.startsWith(currentNorm)) {
                next = incoming; // cumulative
              } else if (incomingNorm.includes(currentNorm)) {
                // cumulative but may not start with the exact same prefix (e.g. leading whitespace changes)
                next = incoming;
              } else if (currentNorm.startsWith(incomingNorm)) {
                next = current; // incoming is older/shorter
              } else if (currentNorm.includes(incomingNorm)) {
                next = current; // duplicate chunk
              } else {
                // overlap: append only the non-overlapping suffix of incoming
                let overlap = 0;
                const max = Math.min(currentNorm.length, incomingNorm.length);
                for (let k = max; k > 0; k--) {
                  if (currentNorm.endsWith(incomingNorm.slice(0, k))) {
                    overlap = k;
                    break;
                  }
                }

                if (overlap > 0) {
                  // Use normalized overlap length to find a safe raw slicing point.
                  // Prefer a direct "startsWith" overlap on raw as a fallback.
                  let rawOverlap = 0;
                  const rawMax = Math.min(current.length, incoming.length);
                  for (let k = rawMax; k > 0; k--) {
                    if (current.endsWith(incoming.slice(0, k))) {
                      rawOverlap = k;
                      break;
                    }
                  }
                  next = rawOverlap > 0 ? current + incoming.slice(rawOverlap) : incoming;
                } else {
                  next = current + incoming;
                }
              }

              assistantMessageRef.current = next;
              upsertAssistantMessage(stripThinkTags(next));
            }
          } catch {
            // ignore malformed SSE chunks
          }
        }
       }


      // Persist sources for this assistant message (so history can be restored later).
      try {
        const finalText = stripThinkTags(assistantMessageRef.current || '');
        const finalSources = assistantSourcesRef.current || [];
        saveSourcesForAssistantMessage(selectedChatId, selectedSessionId, finalText, finalSources);
      } catch {
        // ignore
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
      if (selectedChatId && selectedSessionId) {
        sendMessage();
      }
    }
  };

  return (
    <div data-testid="chat-page" style={{ height: 'calc(100vh - 120px)', display: 'flex', gap: '16px' }}>
      <div style={{ width: '320px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div data-testid="chat-list"
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
                data-testid={`chat-item-${chat.id}`}
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

        <div data-testid="chat-sessions"
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
              data-testid="chat-session-create"
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
                data-testid={`chat-session-item-${s.id}`}
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
                    setRenameDialog({ show: true, sessionId: s.id, value: s.name || '' });
                  }}
                  data-testid={`chat-session-rename-${s.id}`}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '4px',
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
                    setDeleteConfirm({ show: true, sessionId: s.id, sessionName: s.name || s.id });
                  }}
                  data-testid={`chat-session-delete-${s.id}`}
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

      <div data-testid="chat-panel"
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
        <div data-testid="chat-header" style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', fontWeight: 600 }}>
          {selectedChatId ? '对话' : '请选择聊天助手开始对话'}
        </div>

        <div data-testid="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
          {!selectedChatId ? (
            <div style={{ color: '#6b7280' }}>请先选择聊天助手</div>
          ) : !selectedSessionId ? (
            <div style={{ color: '#6b7280' }}>
              当前没有会话页签，请先新建一个会话。
              <div style={{ marginTop: '12px' }}>
                <button
                  onClick={createSession}
                  data-testid="chat-create-session-empty"
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
            </div>
          ) : messages.length === 0 ? (
            <div style={{ color: '#6b7280' }}>开始新的对话...</div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                data-testid={`chat-message-${idx}-${m.role}`}
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
                    lineHeight: 1.5,
                    overflowX: 'auto',
                  }}
                >
                  {(() => {
                    const display = m.role === 'assistant' ? stripThinkTags(m.content) : String(m.content ?? '');
                    const markdownText = m.role === 'assistant' ? rewriteCitationLinks(display) : display;
                    const citationIds = m.role === 'assistant' ? extractCitationIds(display) : [];
                    const sources = Array.isArray(m.sources) ? m.sources : [];
                    const uniqueCitationIds = (() => {
                      const out = [];
                      const seen = new Set();
                      for (const id of citationIds) {
                        const raw = sources[id];
                        if (!raw) continue;
                        const src = normalizeSource(raw);
                        const key = String(src.title || src.docId || '').trim();
                        if (!key || seen.has(key)) continue;
                        seen.add(key);
                        out.push(id);
                      }
                      return out;
                    })();
                    const markdownComponents = {
                      p: ({ node, ...props }) => <p style={{ margin: '0 0 10px 0' }} {...props} />,
                      ul: ({ node, ...props }) => <ul style={{ margin: '0 0 10px 18px' }} {...props} />,
                      ol: ({ node, ...props }) => <ol style={{ margin: '0 0 10px 18px' }} {...props} />,
                      pre: ({ node, ...props }) => (
                        <pre
                          style={{
                            margin: '0 0 10px 0',
                            padding: '10px 12px',
                            background: m.role === 'user' ? 'rgba(255,255,255,0.12)' : '#111827',
                            color: m.role === 'user' ? 'white' : '#f9fafb',
                            borderRadius: '8px',
                            overflowX: 'auto',
                          }}
                          {...props}
                        />
                      ),
                      code: ({ node, inline, className, children, ...props }) => (
                        <code
                          className={className}
                          style={
                            inline
                              ? {
                                  padding: '0 6px',
                                  borderRadius: '6px',
                                  background: m.role === 'user' ? 'rgba(255,255,255,0.18)' : '#e5e7eb',
                                }
                              : undefined
                          }
                          {...props}
                        >
                          {children}
                        </code>
                      ),
                      a: ({ node, href, children, ...props }) => {
                        const h = String(href || '');
                        if (m.role === 'assistant' && h.startsWith('#cid-')) {
                          const idRaw = h.slice('#cid-'.length);
                          const id = Number(idRaw);
                          const raw = Number.isFinite(id) ? sources[id] : null;
                          const src = raw ? normalizeSource(raw) : null;
                          const chunk = src?.chunk || '';
                          return (
                            <span
                              onClick={(e) => {
                                e.preventDefault?.();
                                e.stopPropagation?.();
                                onCitationClick(e, { id: Number.isFinite(id) ? id : -1, chunk });
                              }}
                              style={{
                                display: 'inline-block',
                                padding: '0 6px',
                                margin: '0 2px',
                                borderRadius: '999px',
                                background: '#e5e7eb',
                                color: '#111827',
                                fontSize: '0.85em',
                                lineHeight: 1.6,
                                cursor: 'pointer',
                                userSelect: 'none',
                              }}
                              title="点击查看chunk"
                            >
                              {children}
                            </span>
                          );
                        }
                        return (
                          <a
                            {...props}
                            href={href}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: m.role === 'user' ? 'white' : '#2563eb', textDecoration: 'underline' }}
                          >
                            {children}
                          </a>
                        );
                      },
                    };

                    return (
                      <>
                        <ReactMarkdown components={markdownComponents}>
                          {markdownText}
                        </ReactMarkdown>

                        {m.role === 'assistant' && uniqueCitationIds.length > 0 ? (
                          <div style={{ marginTop: '8px', borderTop: '1px solid #e5e7eb', paddingTop: '8px' }}>
                            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '6px' }}>引用文件</div>
                            {uniqueCitationIds.map((id) => {
                              const raw = sources[id];
                              const src = raw ? normalizeSource(raw) : null;
                              const canOpen = Boolean(src?.docId && src?.dataset);
                              return (
                                <div
                                  key={id}
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    gap: '10px',
                                    padding: '6px 8px',
                                    borderRadius: '6px',
                                    background: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    marginBottom: '6px',
                                  }}
                                >
                                  <div style={{ minWidth: 0, flex: 1 }}>
                                    <div style={{ fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                      {src ? src.title : '未知文件'}
                                    </div>

                                  </div>
                                  <div style={{ display: 'flex', gap: '8px' }}>
                                    <button
                                      disabled={!canOpen}
                                      onClick={() => openSourcePreview(raw)}
                                      style={{
                                        padding: '6px 10px',
                                        borderRadius: '6px',
                                        border: '1px solid #d1d5db',
                                        background: canOpen ? '#ffffff' : '#f3f4f6',
                                        color: canOpen ? '#111827' : '#9ca3af',
                                        cursor: canOpen ? 'pointer' : 'not-allowed',
                                      }}
                                    >
                                      查看
                                    </button>
                                    <button
                                      disabled={!canOpen}
                                      onClick={() => {
                                        downloadSource(raw).catch((e) => setError(e?.message || '下载失败'));
                                      }}
                                      style={{
                                        padding: '6px 10px',
                                        borderRadius: '6px',
                                        border: 'none',
                                        background: canOpen ? '#3b82f6' : '#9ca3af',
                                        color: 'white',
                                        cursor: canOpen ? 'pointer' : 'not-allowed',
                                      }}
                                    >
                                      下载
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : null}
                      </>
                    );
                  })()}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div data-testid="chat-error" style={{ padding: '10px 16px', backgroundColor: '#fee2e2', color: '#991b1b' }}>{error}</div>
        )}

        {!selectedChatId ? (
          <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb', color: '#6b7280' }}>
            请先选择聊天助手
          </div>
        ) : !selectedSessionId ? (
          <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb' }}>
            <button
              onClick={createSession}
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
        ) : (
          <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '10px' }}>
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
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
              onClick={sendMessage}
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
        )}
      </div>

      {citationHover && (
        <div
          data-testid="chat-citation-tooltip"
          onMouseLeave={onCitationPopupLeave}
          style={{
            position: 'fixed',
            left: Math.min(Math.max(10, (citationHover.x || 0) - 220), window.innerWidth - 450),
            top: Math.min(Math.max(10, (citationHover.y || 0) - 10), window.innerHeight - 300),
            width: '440px',
            maxWidth: 'calc(100vw - 20px)',
            maxHeight: '280px',
            overflow: 'auto',
            background: '#111827',
            color: '#f9fafb',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: '10px',
            padding: '10px 12px',
            zIndex: 900,
            boxShadow: '0 10px 25px rgba(0,0,0,0.25)',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.45,
          }}
        >
          {citationHover.chunk}
        </div>
      )}

      {deleteConfirm.show && (
        <div
          data-testid="chat-delete-modal"
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
                data-testid="chat-delete-cancel"
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
                data-testid="chat-delete-confirm"
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

      {renameDialog.show && (
        <div
          data-testid="chat-rename-modal"
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
            <h3 style={{ margin: '0 0 12px 0' }}>重命名会话</h3>
            <div style={{ marginBottom: '12px' }}>
              <input
                value={renameDialog.value}
                onChange={(e) => setRenameDialog((prev) => ({ ...prev, value: e.target.value }))}
                data-testid="chat-rename-input"
                placeholder="请输入会话名称"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid #d1d5db',
                  outline: 'none',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={() => setRenameDialog({ show: false, sessionId: null, value: '' })}
                data-testid="chat-rename-cancel"
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
                onClick={confirmRenameSession}
                data-testid="chat-rename-confirm"
                disabled={!String(renameDialog.value || '').trim()}
                style={{
                  flex: 1,
                  padding: '10px',
                  backgroundColor: !String(renameDialog.value || '').trim() ? '#9ca3af' : '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: !String(renameDialog.value || '').trim() ? 'not-allowed' : 'pointer',
                }}
              >
                确定
              </button>
            </div>
          </div>
        </div>
      )}

      {previewDialog.show && (
        <div
          data-testid="chat-preview-modal"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            padding: '16px',
          }}
          onClick={() => setPreviewDialog({ show: false, title: '', loading: false, error: '', payload: null })}
        >
          <div
            style={{
              width: 'min(920px, 100%)',
              maxHeight: '80vh',
              backgroundColor: 'white',
              borderRadius: '10px',
              overflow: 'hidden',
              boxShadow: '0 10px 30px rgba(0,0,0,0.25)',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
              <div style={{ fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{previewDialog.title || '预览'}</div>
              <button
                onClick={() => setPreviewDialog({ show: false, title: '', loading: false, error: '', payload: null })}
                style={{ border: 'none', background: '#ef4444', color: 'white', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer' }}
              >
                关闭
              </button>
            </div>
            <div style={{ padding: '14px', overflow: 'auto' }}>
              {previewDialog.loading ? (
                <div style={{ color: '#6b7280' }}>加载中...</div>
              ) : previewDialog.error ? (
                <div style={{ color: '#991b1b' }}>{previewDialog.error}</div>
              ) : previewDialog.payload ? (
                (() => {
                  const p = previewDialog.payload;
                  if (p.type === 'text') return <pre style={{ whiteSpace: 'pre-wrap' }}>{p.content}</pre>;
                  if (p.type === 'image') return <img alt={p.filename || 'image'} style={{ maxWidth: '100%' }} src={`data:image/${p.image_type || 'png'};base64,${p.content}`} />;
                  if (p.type === 'pdf') return <iframe title="pdf-preview" style={{ width: '100%', height: '70vh', border: 'none' }} src={`data:application/pdf;base64,${p.content}`} />;
                  if (p.type === 'html') return <iframe title="html-preview" style={{ width: '100%', height: '70vh', border: 'none' }} src={`data:text/html;base64,${p.content}`} />;
                  return <div style={{ color: '#6b7280' }}>{p.message || '不支持预览，请下载查看。'}</div>;
                })()
              ) : (
                <div style={{ color: '#6b7280' }}>暂无内容</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat;
