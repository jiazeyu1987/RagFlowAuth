import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const auditApi = {
  listEvents(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/audit/events?${query}` : '/api/audit/events';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },

  async listDocuments(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/knowledge/documents?${query}` : '/api/knowledge/documents';
    const response = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    return Array.isArray(response?.documents) ? response.documents : [];
  },

  async listDocumentVersions(docId) {
    const response = await httpClient.requestJson(
      authBackendUrl(`/api/knowledge/documents/${encodeURIComponent(docId)}/versions`),
      { method: 'GET' }
    );
    return {
      versions: Array.isArray(response?.versions) ? response.versions : [],
      currentDocId: response?.current_doc_id || '',
      logicalDocId: response?.logical_doc_id || '',
    };
  },

  async listDeletions(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/knowledge/deletions?${query}` : '/api/knowledge/deletions';
    const response = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    return Array.isArray(response?.deletions) ? response.deletions : [];
  },

  async listDownloads(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/ragflow/downloads?${query}` : '/api/ragflow/downloads';
    const response = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    return Array.isArray(response?.downloads) ? response.downloads : [];
  },
};
