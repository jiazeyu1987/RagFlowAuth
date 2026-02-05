import { authBackendUrl } from '../../config/backend';
import documentClient, { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';
import { httpClient } from '../../shared/http/httpClient';

export const knowledgeApi = {
  listRagflowDatasets() {
    return httpClient.requestJson(authBackendUrl('/api/datasets'), { method: 'GET' });
  },

  listLocalDocuments(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/knowledge/documents?${query}` : '/api/knowledge/documents';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },

  uploadDocument(file, kbId = '灞曞巺') {
    return documentClient.uploadKnowledge(file, kbId);
  },

  deleteLocalDocument(docId) {
    return documentClient.delete({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
  },

  async downloadLocalDocument(docId) {
    return documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
  },

  async batchDownloadLocalDocuments(docIds) {
    return documentClient.batchDownloadKnowledgeToBrowser(docIds);
  },
};
