import { authBackendUrl } from '../../config/backend';
import { DOCUMENT_SOURCE } from '../../shared/documents/constants';
import { httpClient } from '../../shared/http/httpClient';
import { documentsApi } from '../documents/api';

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const normalizeArrayField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!Array.isArray(envelope[field])) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope[field];
};

const normalizeDatasetEnvelope = (payload, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!envelope.dataset || typeof envelope.dataset !== 'object' || Array.isArray(envelope.dataset)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope.dataset;
};

const normalizeDirectoryTree = (payload, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!Array.isArray(envelope.nodes) || !Array.isArray(envelope.datasets)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return {
    ...envelope,
    nodes: envelope.nodes,
    datasets: envelope.datasets,
  };
};

const normalizeDirectoryNodeEnvelope = (payload, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!envelope.node || typeof envelope.node !== 'object' || Array.isArray(envelope.node)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope.node;
};

function withCompanyId(path, companyId) {
  if (companyId === undefined || companyId === null || companyId === '') return path;
  const query = new URLSearchParams({ company_id: String(companyId) }).toString();
  return `${path}?${query}`;
}

export const knowledgeApi = {
  async listRagflowDatasets() {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/datasets'), { method: 'GET' }),
      'datasets',
      'ragflow_dataset_list'
    );
  },

  async getRagflowDataset(datasetRef) {
    return normalizeDatasetEnvelope(
      await httpClient.requestJson(authBackendUrl(`/api/datasets/${encodeURIComponent(datasetRef)}`), {
        method: 'GET',
      }),
      'ragflow_dataset_get'
    );
  },

  async updateRagflowDataset(datasetRef, updates) {
    return normalizeDatasetEnvelope(
      await httpClient.requestJson(authBackendUrl(`/api/datasets/${encodeURIComponent(datasetRef)}`), {
        method: 'PUT',
        body: JSON.stringify(updates || {}),
      }),
      'ragflow_dataset_update'
    );
  },

  async createRagflowDataset(payload) {
    return normalizeDatasetEnvelope(
      await httpClient.requestJson(authBackendUrl('/api/datasets'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'ragflow_dataset_create'
    );
  },

  deleteRagflowDataset(datasetRef) {
    return httpClient.requestJson(authBackendUrl(`/api/datasets/${encodeURIComponent(datasetRef)}`), {
      method: 'DELETE',
    });
  },

  async listKnowledgeDirectories(options = {}) {
    const path = withCompanyId('/api/knowledge/directories', options.companyId);
    return normalizeDirectoryTree(
      await httpClient.requestJson(authBackendUrl(path), { method: 'GET' }),
      'knowledge_directory_tree'
    );
  },

  async createKnowledgeDirectory(payload, options = {}) {
    const path = withCompanyId('/api/knowledge/directories', options.companyId);
    return normalizeDirectoryNodeEnvelope(
      await httpClient.requestJson(authBackendUrl(path), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'knowledge_directory_create'
    );
  },

  async updateKnowledgeDirectory(nodeId, payload) {
    return normalizeDirectoryNodeEnvelope(
      await httpClient.requestJson(authBackendUrl(`/api/knowledge/directories/${encodeURIComponent(nodeId)}`), {
        method: 'PUT',
        body: JSON.stringify(payload || {}),
      }),
      'knowledge_directory_update'
    );
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

  deleteLocalDocument(docId) {
    return documentsApi.deleteDocument({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
  },

  async downloadLocalDocument(docId) {
    return documentsApi.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
  },

  async batchDownloadLocalDocuments(docIds) {
    return documentsApi.batchDownloadKnowledgeToBrowser(docIds);
  },
};
