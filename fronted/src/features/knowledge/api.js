import { authBackendUrl } from '../../config/backend';
import documentClient, { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';
import { httpClient } from '../../shared/http/httpClient';

function unwrapEnvelope(res) {
  if (!res || typeof res !== 'object') return res;
  if (res.dataset && typeof res.dataset === 'object') return res.dataset;
  if (res.chat && typeof res.chat === 'object') return res.chat;
  if (res.config && typeof res.config === 'object') return res.config;
  if (res.data && typeof res.data === 'object') {
    if (res.data.dataset && typeof res.data.dataset === 'object') return res.data.dataset;
    if (res.data.chat && typeof res.data.chat === 'object') return res.data.chat;
    if (res.data.config && typeof res.data.config === 'object') return res.data.config;
  }
  return res;
}

export const knowledgeApi = {
  listRagflowDatasets() {
    return httpClient.requestJson(authBackendUrl('/api/datasets'), { method: 'GET' });
  },

  async getRagflowDataset(datasetRef) {
    const res = await httpClient.requestJson(authBackendUrl(`/api/datasets/${encodeURIComponent(datasetRef)}`), {
      method: 'GET',
    });
    return unwrapEnvelope(res);
  },

  async updateRagflowDataset(datasetRef, updates) {
    const res = await httpClient.requestJson(authBackendUrl(`/api/datasets/${encodeURIComponent(datasetRef)}`), {
      method: 'PUT',
      body: JSON.stringify(updates || {}),
    });
    return unwrapEnvelope(res);
  },

  async createRagflowDataset(payload) {
    const res = await httpClient.requestJson(authBackendUrl('/api/datasets'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return unwrapEnvelope(res);
  },

  deleteRagflowDataset(datasetRef) {
    return httpClient.requestJson(authBackendUrl(`/api/datasets/${encodeURIComponent(datasetRef)}`), {
      method: 'DELETE',
    });
  },

  listKnowledgeDirectories() {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/directories'), { method: 'GET' });
  },

  createKnowledgeDirectory(payload) {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/directories'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  updateKnowledgeDirectory(nodeId, payload) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/directories/${encodeURIComponent(nodeId)}`), {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    });
  },

  deleteKnowledgeDirectory(nodeId) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/directories/${encodeURIComponent(nodeId)}`), {
      method: 'DELETE',
    });
  },

  assignDatasetDirectory(datasetRef, nodeId) {
    return httpClient.requestJson(
      authBackendUrl(`/api/knowledge/directories/datasets/${encodeURIComponent(datasetRef)}/node`),
      {
        method: 'PUT',
        body: JSON.stringify({ node_id: nodeId || null }),
      }
    );
  },

  listRagflowChats(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/chats?${query}` : '/api/chats';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },

  async getRagflowChat(chatId) {
    const res = await httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}`), { method: 'GET' });
    return unwrapEnvelope(res);
  },

  async createRagflowChat(payload) {
    const res = await httpClient.requestJson(authBackendUrl('/api/chats'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return unwrapEnvelope(res);
  },

  async updateRagflowChat(chatId, updates) {
    const res = await httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}`), {
      method: 'PUT',
      body: JSON.stringify(updates || {}),
    });
    return unwrapEnvelope(res);
  },

  deleteRagflowChat(chatId) {
    return httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}`), {
      method: 'DELETE',
    });
  },

  clearRagflowChatParsedFiles(chatId) {
    return httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}/clear-parsed-files`), {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  listSearchConfigs() {
    return httpClient.requestJson(authBackendUrl('/api/search/configs'), { method: 'GET' });
  },

  async getSearchConfig(configId) {
    const res = await httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'GET',
    });
    return unwrapEnvelope(res);
  },

  async createSearchConfig(payload) {
    const res = await httpClient.requestJson(authBackendUrl('/api/search/configs'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return unwrapEnvelope(res);
  },

  async updateSearchConfig(configId, updates) {
    const res = await httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'PUT',
      body: JSON.stringify(updates || {}),
    });
    return unwrapEnvelope(res);
  },

  deleteSearchConfig(configId) {
    return httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'DELETE',
    });
  },

  listLocalDocuments(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/knowledge/documents?${query}` : '/api/knowledge/documents';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },

  uploadDocument(file, kbId = '展厅') {
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
