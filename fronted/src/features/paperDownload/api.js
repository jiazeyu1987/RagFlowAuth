import { authBackendUrl } from '../../config/backend';
import { DOCUMENT_SOURCE } from '../../shared/documents/constants';
import { httpClient } from '../../shared/http/httpClient';

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const normalizeStopSessionResult = (payload) => {
  const envelope = assertObjectPayload(payload, 'paper_download_stop_session');
  if (!envelope.result || typeof envelope.result !== 'object' || Array.isArray(envelope.result)) {
    throw new Error('paper_download_stop_session_invalid_payload');
  }
  const result = envelope.result;
  if (typeof result.message !== 'string' || !result.message.trim()) {
    throw new Error('paper_download_stop_session_invalid_payload');
  }
  if (typeof result.session_id !== 'string' || !result.session_id.trim()) {
    throw new Error('paper_download_stop_session_invalid_payload');
  }
  if (typeof result.status !== 'string' || !result.status.trim()) {
    throw new Error('paper_download_stop_session_invalid_payload');
  }
  if (typeof result.already_finished !== 'boolean') {
    throw new Error('paper_download_stop_session_invalid_payload');
  }
  return result;
};

const DEFAULT_LOCAL_KB = '[鏈湴璁烘枃]';

export const paperDownloadApi = {
  parseKeywords(keywordText) {
    return String(keywordText || '')
      .split(/[,;\n\r锛岋紱]+/)
      .map((v) => v.trim())
      .filter((v, idx, arr) => v && arr.findIndex((x) => x.toLowerCase() === v.toLowerCase()) === idx);
  },

  createSession({ keywordText, useAnd, autoAnalyze, sources }) {
    return httpClient.requestJson(authBackendUrl('/api/paper-download/sessions'), {
      method: 'POST',
      body: JSON.stringify({
        keyword_text: String(keywordText || ''),
        use_and: Boolean(useAnd),
        auto_analyze: Boolean(autoAnalyze),
        sources: sources || {},
      }),
    });
  },

  getSession(sessionId) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-download/sessions/${encodeURIComponent(sessionId)}`), {
      method: 'GET',
    });
  },

  async stopSession(sessionId) {
    return normalizeStopSessionResult(
      await httpClient.requestJson(authBackendUrl(`/api/paper-download/sessions/${encodeURIComponent(sessionId)}/stop`), {
        method: 'POST',
      })
    );
  },

  listHistoryKeywords() {
    return httpClient.requestJson(authBackendUrl('/api/paper-download/history/keywords'), { method: 'GET' });
  },

  getHistoryByKeyword(historyKey) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-download/history/keywords/${encodeURIComponent(historyKey)}`), {
      method: 'GET',
    });
  },

  addHistoryToLocalKb(historyKey, kbRef = DEFAULT_LOCAL_KB) {
    return httpClient.requestJson(
      authBackendUrl(`/api/paper-download/history/keywords/${encodeURIComponent(historyKey)}/add-all-to-local-kb`),
      {
        method: 'POST',
        body: JSON.stringify({ kb_ref: kbRef }),
      }
    );
  },

  deleteHistoryKeyword(historyKey) {
    return httpClient.requestJson(authBackendUrl('/api/paper-download/history/keywords/delete'), {
      method: 'POST',
      body: JSON.stringify({ history_key: String(historyKey || '') }),
    });
  },

  addItemToLocalKb(sessionId, itemId, kbRef = DEFAULT_LOCAL_KB) {
    return httpClient.requestJson(
      authBackendUrl(`/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(itemId)}/add-to-local-kb`),
      {
        method: 'POST',
        body: JSON.stringify({ kb_ref: kbRef }),
      }
    );
  },

  addAllToLocalKb(sessionId, kbRef = DEFAULT_LOCAL_KB) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-download/sessions/${encodeURIComponent(sessionId)}/add-all-to-local-kb`), {
      method: 'POST',
      body: JSON.stringify({ kb_ref: kbRef }),
    });
  },

  deleteItem(sessionId, itemId, { deleteLocalKb = true } = {}) {
    const path =
      `/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(itemId)}` +
      `?delete_local_kb=${deleteLocalKb ? 'true' : 'false'}`;
    return httpClient.requestJson(authBackendUrl(path), { method: 'DELETE' });
  },

  deleteSession(sessionId, { deleteLocalKb = true } = {}) {
    const path = `/api/paper-download/sessions/${encodeURIComponent(sessionId)}?delete_local_kb=${deleteLocalKb ? 'true' : 'false'}`;
    return httpClient.requestJson(authBackendUrl(path), { method: 'DELETE' });
  },

  toPreviewTarget(sessionId, item) {
    if (!item || !sessionId) return null;
    return {
      source: DOCUMENT_SOURCE.PAPER,
      docId: item.item_id,
      sessionId,
      title: item.title || item.filename || `paper_${item.item_id}`,
      filename: item.filename || '',
    };
  },
};

export default paperDownloadApi;
