import { authBackendUrl } from '../../config/backend';
import { DOCUMENT_SOURCE, documentsApi } from '../documents/api';
import { httpClient } from '../../shared/http/httpClient';

function unwrapEnvelope(res) {
  if (!res || typeof res !== 'object') return res;
  if (res.dataset && typeof res.dataset === 'object') return res.dataset;
  if (res.data && typeof res.data === 'object') {
    if (res.data.dataset && typeof res.data.dataset === 'object') return res.data.dataset;
  }
  return res;
}

function withCompanyId(path, companyId) {
  if (companyId === undefined || companyId === null || companyId === '') return path;
  const query = new URLSearchParams({ company_id: String(companyId) }).toString();
  return `${path}?${query}`;
}

export const knowledgeApi = {
  async listRagflowDatasets() {
    const response = await httpClient.requestJson(authBackendUrl('/api/datasets'), { method: 'GET' });
    if (!Array.isArray(response?.datasets)) {
      throw new Error('ragflow_dataset_list_invalid_payload');
    }
    return response.datasets;
  },

  async listRagflowDocuments(datasetName = '灞曞巺') {
    const query = new URLSearchParams({
      dataset_name: String(datasetName || ''),
    }).toString();
    const response = await httpClient.requestJson(authBackendUrl(`/api/ragflow/documents?${query}`), {
      method: 'GET',
    });
    return Array.isArray(response?.documents) ? response.documents : [];
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

  listKnowledgeDirectories(options = {}) {
    const path = withCompanyId('/api/knowledge/directories', options.companyId);
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },

  createKnowledgeDirectory(payload, options = {}) {
    const path = withCompanyId('/api/knowledge/directories', options.companyId);
    return httpClient.requestJson(authBackendUrl(path), {
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

  listLocalDocuments(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/knowledge/documents?${query}` : '/api/knowledge/documents';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },

  async listDocuments(params = {}) {
    const response = await this.listLocalDocuments(params);
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
  getAllowedUploadExtensions() {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/settings/allowed-extensions'), { method: 'GET' });
  },

  updateAllowedUploadExtensions(allowedExtensions, changeReason) {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/settings/allowed-extensions'), {
      method: 'PUT',
      body: JSON.stringify({
        allowed_extensions: allowedExtensions || [],
        change_reason: changeReason,
      }),
    });
  },
  uploadDocument(file, kbId = '展厅') {
    return documentsApi.uploadKnowledge(file, kbId);
  },

  deleteLocalDocument(docId) {
    return documentsApi.deleteDocument({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
  },

  async downloadLocalDocument(docId) {
    return documentsApi.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
  },

  async batchDownloadLocalDocuments(docIds) {
    return documentsApi.batchDownloadKnowledgeToBrowser(docIds);
  },

  transferRagflowDocument(docId, sourceDatasetName, targetDatasetName, operation = 'copy') {
    return httpClient.requestJson(
      authBackendUrl(`/api/ragflow/documents/${encodeURIComponent(docId)}/transfer`),
      {
        method: 'POST',
        body: JSON.stringify({
          source_dataset_name: sourceDatasetName,
          target_dataset_name: targetDatasetName,
          operation,
        }),
      }
    );
  },
};

