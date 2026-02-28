import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';
import { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';

const DEFAULT_LOCAL_KB = '[本地专利]';

class PatentDownloadManager {
  parseKeywords(keywordText) {
    return String(keywordText || '')
      .split(/[,;\n\r，；]+/)
      .map((v) => v.trim())
      .filter((v, idx, arr) => v && arr.findIndex((x) => x.toLowerCase() === v.toLowerCase()) === idx);
  }

  async createSession({ keywordText, useAnd, autoAnalyze, sources }) {
    return httpClient.requestJson(authBackendUrl('/api/patent-download/sessions'), {
      method: 'POST',
      body: JSON.stringify({
        keyword_text: String(keywordText || ''),
        use_and: Boolean(useAnd),
        auto_analyze: Boolean(autoAnalyze),
        sources: sources || {},
      }),
    });
  }

  async getSession(sessionId) {
    return httpClient.requestJson(authBackendUrl(`/api/patent-download/sessions/${encodeURIComponent(sessionId)}`), {
      method: 'GET',
    });
  }

  async stopSession(sessionId) {
    return httpClient.requestJson(authBackendUrl(`/api/patent-download/sessions/${encodeURIComponent(sessionId)}/stop`), {
      method: 'POST',
    });
  }

  async listHistoryKeywords() {
    return httpClient.requestJson(authBackendUrl('/api/patent-download/history/keywords'), {
      method: 'GET',
    });
  }

  async getHistoryByKeyword(historyKey) {
    return httpClient.requestJson(
      authBackendUrl(`/api/patent-download/history/keywords/${encodeURIComponent(historyKey)}`),
      { method: 'GET' }
    );
  }

  async deleteHistoryKeyword(historyKey) {
    return httpClient.requestJson(authBackendUrl('/api/patent-download/history/keywords/delete'), {
      method: 'POST',
      body: JSON.stringify({ history_key: String(historyKey || '') }),
    });
  }

  async addItemToLocalKb(sessionId, itemId, kbRef = DEFAULT_LOCAL_KB) {
    return httpClient.requestJson(
      authBackendUrl(
        `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(itemId)}/add-to-local-kb`
      ),
      {
        method: 'POST',
        body: JSON.stringify({ kb_ref: kbRef }),
      }
    );
  }

  async addAllToLocalKb(sessionId, kbRef = DEFAULT_LOCAL_KB) {
    return httpClient.requestJson(
      authBackendUrl(`/api/patent-download/sessions/${encodeURIComponent(sessionId)}/add-all-to-local-kb`),
      {
        method: 'POST',
        body: JSON.stringify({ kb_ref: kbRef }),
      }
    );
  }

  async deleteItem(sessionId, itemId, { deleteLocalKb = true } = {}) {
    const path =
      `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(itemId)}` +
      `?delete_local_kb=${deleteLocalKb ? 'true' : 'false'}`;
    return httpClient.requestJson(authBackendUrl(path), { method: 'DELETE' });
  }

  async deleteSession(sessionId, { deleteLocalKb = true } = {}) {
    const path =
      `/api/patent-download/sessions/${encodeURIComponent(sessionId)}` +
      `?delete_local_kb=${deleteLocalKb ? 'true' : 'false'}`;
    return httpClient.requestJson(authBackendUrl(path), { method: 'DELETE' });
  }

  toPreviewTarget(sessionId, item) {
    if (!item || !sessionId) return null;
    return {
      source: DOCUMENT_SOURCE.PATENT,
      docId: item.item_id,
      sessionId,
      title: item.title || item.filename || `patent_${item.item_id}`,
      filename: item.filename || '',
    };
  }
}

const patentDownloadManager = new PatentDownloadManager();
export default patentDownloadManager;
