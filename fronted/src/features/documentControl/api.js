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
  appendIfPresent(formData, 'file_subtype', payload.file_subtype);
  appendIfPresent(formData, 'usage_scope', payload.usage_scope);
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

  async submitRevisionForApproval(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/approval/submit`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_revision_approval_submit'
    );
  },

  async previewRevisionApprovalMatrix(controlledRevisionId) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/matrix-preview`
        ),
        { method: 'GET' }
      ),
      'result',
      'document_control_revision_matrix_preview'
    );
  },

  async approveRevisionStep(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/approval/approve`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_revision_approval_approve'
    );
  },

  async rejectRevisionStep(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/approval/reject`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_revision_approval_reject'
    );
  },

  async addSignRevisionStep(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/approval/add-sign`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_revision_approval_add_sign'
    );
  },

  async remindOverdueApprovalStep(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/approval/remind-overdue`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'result',
      'document_control_approval_remind_overdue'
    );
  },

  async getDistributionDepartments(controlledDocumentId) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/documents/${encodeURIComponent(
            controlledDocumentId
          )}/distribution-departments`
        ),
        { method: 'GET' }
      ),
      'department_ids',
      'document_control_distribution_departments_get'
    );
  },

  async setDistributionDepartments(controlledDocumentId, payload) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/documents/${encodeURIComponent(
            controlledDocumentId
          )}/distribution-departments`
        ),
        {
          method: 'PUT',
          body: JSON.stringify(payload || {}),
        }
      ),
      'department_ids',
      'document_control_distribution_departments_set'
    );
  },

  async publishRevision(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/publish`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_revision_publish'
    );
  },

  async completeManualReleaseArchive(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/publish/manual-archive-complete`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_manual_release_complete'
    );
  },

  async listRevisionDepartmentAcks(controlledRevisionId) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/department-acks`
        ),
        { method: 'GET' }
      ),
      'items',
      'document_control_department_acks_list'
    );
  },

  async confirmRevisionDepartmentAck(controlledRevisionId, departmentId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/department-acks/${encodeURIComponent(departmentId)}/confirm`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'ack',
      'document_control_department_ack_confirm'
    );
  },

  async remindOverdueRevisionDepartmentAcks(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/department-acks/remind-overdue`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'result',
      'document_control_department_ack_remind'
    );
  },

  async initiateObsoleteRevision(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/obsolete/initiate`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_obsolete_initiate'
    );
  },

  async approveObsoleteRevision(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/obsolete/approve`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_obsolete_approve'
    );
  },

  async confirmRevisionDestruction(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/doc-control/revisions/${encodeURIComponent(
            controlledRevisionId
          )}/obsolete/destruction/confirm`
        ),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'document',
      'document_control_destruction_confirm'
    );
  },

  async listRetiredDocuments({ kbId, limit = 100 } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/retired-documents${buildQuery({
            kb_id: kbId,
            limit,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'document_control_retired_documents_list'
    );
  },
};

export default documentControlApi;
