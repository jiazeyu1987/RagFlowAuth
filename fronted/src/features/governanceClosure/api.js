import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const ensureObject = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const ensureArrayField = (payload, field, action) => {
  const body = ensureObject(payload, action);
  if (!Array.isArray(body[field])) {
    throw new Error(`${action}_invalid_payload`);
  }
  return body[field];
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

const governanceClosureApi = {
  async listComplaints(filters = {}) {
    return ensureArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/complaints/cases${buildQuery({ status: filters.status, limit: filters.limit ?? 50 })}`),
        { method: 'GET' }
      ),
      'items',
      'ws08_list_complaints'
    );
  },

  async createComplaint(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/complaints/cases'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return ensureObject(response.complaint, 'ws08_create_complaint');
  },

  async listCapas(filters = {}) {
    return ensureArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/capa/actions${buildQuery({ status: filters.status, limit: filters.limit ?? 50 })}`),
        { method: 'GET' }
      ),
      'items',
      'ws08_list_capa'
    );
  },

  async createCapa(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/capa/actions'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return ensureObject(response.capa, 'ws08_create_capa');
  },

  async listInternalAudits(filters = {}) {
    return ensureArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/internal-audits/records${buildQuery({ status: filters.status, limit: filters.limit ?? 50 })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'ws08_list_internal_audit'
    );
  },

  async createInternalAudit(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/internal-audits/records'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return ensureObject(response.audit_record, 'ws08_create_internal_audit');
  },

  async listManagementReviews(filters = {}) {
    return ensureArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/management-reviews/records${buildQuery({ status: filters.status, limit: filters.limit ?? 50 })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'ws08_list_management_review'
    );
  },

  async createManagementReview(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/management-reviews/records'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return ensureObject(response.management_review, 'ws08_create_management_review');
  },
};

export default governanceClosureApi;
