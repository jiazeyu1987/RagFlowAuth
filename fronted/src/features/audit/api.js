import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

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

const normalizeCountField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  const value = envelope[field];
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

export const auditApi = {
  async listEvents(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/audit/events?${query}` : '/api/audit/events';
    const payload = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    return {
      total: normalizeCountField(payload, 'total', 'audit_events_list'),
      items: normalizeArrayField(payload, 'items', 'audit_events_list'),
    };
  },

  async listDocuments(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/knowledge/documents?${query}` : '/api/knowledge/documents';
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl(path), { method: 'GET' }),
      'documents',
      'audit_documents_list'
    );
  },

  async listDocumentVersions(docId) {
    const response = assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/knowledge/documents/${encodeURIComponent(docId)}/versions`),
        { method: 'GET' }
      ),
      'audit_document_versions_list'
    );
    const versions = response.versions;
    if (!Array.isArray(versions)) {
      throw new Error('audit_document_versions_list_invalid_payload');
    }
    return {
      versions,
      currentDocId: response?.current_doc_id || '',
      logicalDocId: response?.logical_doc_id || '',
    };
  },

  async listDeletions(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/knowledge/deletions?${query}` : '/api/knowledge/deletions';
    const payload = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    normalizeCountField(payload, 'count', 'audit_deletions_list');
    return normalizeArrayField(payload, 'deletions', 'audit_deletions_list');
  },

  async listDownloads(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/ragflow/downloads?${query}` : '/api/ragflow/downloads';
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl(path), { method: 'GET' }),
      'downloads',
      'audit_downloads_list'
    );
  },
};
