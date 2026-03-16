const SOURCE_KEY_PREFIX = 'ragflowauth_chat_sources_v1';

export const extractCitationIds = (value) => {
  const text = String(value ?? '');
  const ids = new Set();
  const re = /\[ID:(\d+)\]/g;
  let match = null;
  while ((match = re.exec(text)) !== null) {
    const n = Number(match[1]);
    if (!Number.isNaN(n)) ids.add(n);
  }
  return Array.from(ids).sort((a, b) => a - b);
};

export const normalizeSource = (src) => {
  const s = src && typeof src === 'object' ? src : {};
  const docId = s.doc_id || s.docId || s.document_id || s.documentId || s.ragflow_doc_id || s.ragflowDocId || s.id || '';
  const dataset = s.dataset_id || s.datasetId || s.dataset || s.dataset_name || s.datasetName || s.kb_id || s.kbId || s.kb_name || s.kbName || '';
  const title = s.filename || s.doc_name || s.docName || s.document_name || s.documentName || s.name || s.title || docId || '未命名';
  const chunk = s.chunk || s.chunk_text || s.chunkText || s.content || s.text || '';
  return {
    docId: String(docId || ''),
    dataset: String(dataset || ''),
    title: String(title || ''),
    chunk: String(chunk || ''),
  };
};

export const rewriteCitationLinks = (text) => {
  const input = String(text ?? '');
  return input.replace(/\[ID:(\d+)\]/g, (_m, id) => `[ID:${id}](#cid-${id})`);
};

export const computeMessageKey = (chatId, sessionId, content) => {
  const text = String(content ?? '');
  let hash = 5381;
  for (let i = 0; i < text.length; i++) {
    hash = ((hash << 5) + hash) ^ text.charCodeAt(i);
    hash >>>= 0;
  }
  return `${SOURCE_KEY_PREFIX}:${String(chatId || '')}:${String(sessionId || '')}:${hash.toString(16)}`;
};

export const saveSourcesForAssistantMessage = (chatId, sessionId, content, sources, debugLog = null) => {
  const list = Array.isArray(sources) ? sources : [];
  if (!chatId || !sessionId || !content || list.length === 0) return;

  try {
    const key = computeMessageKey(chatId, sessionId, content);
    window.localStorage.setItem(key, JSON.stringify(list));
    if (typeof debugLog === 'function') {
      debugLog('保存来源成功', { key, count: list.length });
    }
  } catch (e) {
    if (typeof debugLog === 'function') {
      debugLog('保存来源失败', { error: e?.message || String(e || '') });
    }
  }
};

export const loadSourcesForAssistantMessage = (chatId, sessionId, content) => {
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
};

export const restoreSourcesIntoMessages = (chatId, sessionId, messageList, stripThinkTags) => {
  const msgs = Array.isArray(messageList) ? messageList : [];
  const stripFn = typeof stripThinkTags === 'function' ? stripThinkTags : (v) => String(v ?? '');

  return msgs.map((m) => {
    if (!m || typeof m !== 'object') return m;
    if (m.role !== 'assistant') return m;
    const content = stripFn(m.content);
    const existing = Array.isArray(m.sources) ? m.sources : [];
    if (existing.length > 0) return m;
    const restored = loadSourcesForAssistantMessage(chatId, sessionId, content);
    if (Array.isArray(restored) && restored.length > 0) {
      return { ...m, sources: restored };
    }
    return m;
  });
};
