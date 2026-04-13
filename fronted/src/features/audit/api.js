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

const buildQueryString = (params = {}) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    query.set(key, String(value));
  });
  return query.toString();
};

const parseMaybeJson = async (response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

const parseContentDispositionFilename = (contentDisposition, fallbackName) => {
  let filename = fallbackName;
  const header = String(contentDisposition || '');
  if (!header) return filename;

  const utf8Match = header.match(/filename\*=UTF-8''([^;\s]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);

  const filenameMatch = header.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  if (filenameMatch?.[1]) return filenameMatch[1].replace(/['"]/g, '');

  return filename;
};

const saveResponseToBrowser = async (response, fallbackName) => {
  const filename = parseContentDispositionFilename(
    response.headers?.get?.('Content-Disposition'),
    fallbackName
  );
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return { success: true, filename };
};

export const auditApi = {
  async listEvents(params = {}) {
    const query = buildQueryString(params);
    const path = query ? `/api/audit/events?${query}` : '/api/audit/events';
    const payload = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    return {
      total: normalizeCountField(payload, 'total', 'audit_events_list'),
      items: normalizeArrayField(payload, 'items', 'audit_events_list'),
    };
  },

  async listDocuments(params = {}) {
    const query = buildQueryString(params);
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
    const query = buildQueryString(params);
    const path = query ? `/api/knowledge/deletions?${query}` : '/api/knowledge/deletions';
    const payload = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    normalizeCountField(payload, 'count', 'audit_deletions_list');
    return normalizeArrayField(payload, 'deletions', 'audit_deletions_list');
  },

  async listDownloads(params = {}) {
    const query = buildQueryString(params);
    const path = query ? `/api/ragflow/downloads?${query}` : '/api/ragflow/downloads';
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl(path), { method: 'GET' }),
      'downloads',
      'audit_downloads_list'
    );
  },

  async exportEvidence(params = {}) {
    const query = buildQueryString(params);
    const path = query ? `/api/audit/evidence-export?${query}` : '/api/audit/evidence-export';
    const response = await httpClient.request(authBackendUrl(path), { method: 'GET' });
    if (!response.ok) {
      const payload = await parseMaybeJson(response);
      const message =
        payload?.detail || payload?.message || payload?.error || `Request failed (${response.status})`;
      const error = new Error(message);
      error.status = response.status;
      error.data = payload;
      throw error;
    }
    return saveResponseToBrowser(response, `inspection_evidence_${Date.now()}.zip`);
  },
};
