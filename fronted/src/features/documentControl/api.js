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

const normalizeObjectField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  const value = envelope[field];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

const buildQuery = (params = {}) => {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : '';
};

const appendIfPresent = (formData, key, value) => {
  if (value === undefined || value === null || value === '') return;
  formData.append(key, value);
};

const buildDocumentFormData = (payload = {}) => {
  const formData = new FormData();
  appendIfPresent(formData, 'doc_code', payload.doc_code);
  appendIfPresent(formData, 'title', payload.title);
  appendIfPresent(formData, 'document_type', payload.document_type);
  appendIfPresent(formData, 'target_kb_id', payload.target_kb_id);
  appendIfPresent(formData, 'product_name', payload.product_name);
  appendIfPresent(formData, 'registration_ref', payload.registration_ref);
  appendIfPresent(formData, 'change_summary', payload.change_summary);
  if (payload.file) formData.append('file', payload.file);
  return formData;
};

const buildRevisionFormData = (payload = {}) => {
  const formData = new FormData();
  appendIfPresent(formData, 'change_summary', payload.change_summary);
  if (payload.file) formData.append('file', payload.file);
  return formData;
};

export const documentControlApi = {
  async listDocuments(filters = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/documents${buildQuery({
            limit: filters.limit ?? 100,
            doc_code: filters.docCode,
            title: filters.title,
            document_type: filters.documentType,
            product_name: filters.productName,
            registration_ref: filters.registrationRef,
            status: filters.status,
            query: filters.query,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'document_control_documents_list'
    );
  },

  async getDocument(controlledDocumentId) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/doc-control/documents/${controlledDocumentId}`),
        { method: 'GET' }
      ),
      'document',
      'document_control_document_get'
    );
  },

  async createDocument(payload) {
    return normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/quality-system/doc-control/documents'), {
        method: 'POST',
        body: buildDocumentFormData(payload),
      }),
      'document',
      'document_control_document_create'
    );
  },

  async createRevision(controlledDocumentId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/doc-control/documents/${controlledDocumentId}/revisions`),
        {
          method: 'POST',
          body: buildRevisionFormData(payload),
        }
      ),
      'document',
      'document_control_revision_create'
    );
  },

  async transitionRevision(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/doc-control/revisions/${controlledRevisionId}/transitions`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_revision_transition'
    );
  },
};

export default documentControlApi;
