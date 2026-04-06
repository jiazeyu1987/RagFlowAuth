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

const normalizeResultEnvelope = (payload, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!envelope.result || typeof envelope.result !== 'object' || Array.isArray(envelope.result)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof envelope.result.message !== 'string' || !envelope.result.message.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope.result;
};

const normalizeDirectoryAssignmentResult = (payload, action) => {
  const result = normalizeResultEnvelope(payload, action);
  if (typeof result.dataset_id !== 'string' || !result.dataset_id.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!Object.prototype.hasOwnProperty.call(result, 'node_id')) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (result.node_id !== null && typeof result.node_id !== 'string') {
    throw new Error(`${action}_invalid_payload`);
  }
  return result;
};

const normalizeApprovalRequestEnvelope = (payload, action) => {
  const envelope = assertObjectPayload(payload, action);
  const request = envelope.request;
  if (!request || typeof request !== 'object' || Array.isArray(request)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof request.request_id !== 'string' || !request.request_id.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return request;
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

  async deleteRagflowDataset(datasetRef) {
    return normalizeApprovalRequestEnvelope(
      await httpClient.requestJson(authBackendUrl(`/api/datasets/${encodeURIComponent(datasetRef)}`), {
        method: 'DELETE',
      }),
      'ragflow_dataset_delete'
    );
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

  async deleteKnowledgeDirectory(nodeId) {
    return normalizeResultEnvelope(
      await httpClient.requestJson(authBackendUrl(`/api/knowledge/directories/${encodeURIComponent(nodeId)}`), {
        method: 'DELETE',
      }),
      'knowledge_directory_delete'
    );
  },

  async assignDatasetDirectory(datasetRef, nodeId) {
    return normalizeDirectoryAssignmentResult(
      await httpClient.requestJson(
        authBackendUrl(`/api/knowledge/directories/datasets/${encodeURIComponent(datasetRef)}/node`),
        {
          method: 'PUT',
          body: JSON.stringify({ node_id: nodeId || null }),
        }
      ),
      'knowledge_directory_assign'
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
