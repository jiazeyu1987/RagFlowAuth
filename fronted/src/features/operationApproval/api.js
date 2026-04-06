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

const normalizeInboxPayload = (payload) => ({
  items: normalizeArrayField(payload, 'items', 'operation_approval_inbox_list'),
  count: normalizeCountField(payload, 'count', 'operation_approval_inbox_list'),
  unreadCount: normalizeCountField(payload, 'unread_count', 'operation_approval_inbox_list'),
});

const buildQuery = (params = {}) => {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : '';
};

export const operationApprovalApi = {
  async listWorkflows() {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/operation-approvals/workflows'), { method: 'GET' }),
      'items',
      'operation_approval_workflows_list'
    );
  },

  updateWorkflow(operationType, payload) {
    return httpClient.requestJson(
      authBackendUrl(`/api/operation-approvals/workflows/${encodeURIComponent(operationType)}`),
      {
        method: 'PUT',
        body: JSON.stringify(payload || {}),
      }
    );
  },

  async listRequests({ view = 'mine', status = 'all', limit = 100 } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/operation-approvals/requests${buildQuery({
            view,
            status: status && status !== 'all' ? status : '',
            limit,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'operation_approval_requests_list'
    );
  },

  async listTodos({ limit = 100 } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/operation-approvals/todos${buildQuery({ limit })}`),
        { method: 'GET' }
      ),
      'items',
      'operation_approval_todos_list'
    );
  },

  async getRequest(requestId) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}`),
        { method: 'GET' }
      ),
      'operation_approval_request_get'
    );
  },

  async getStats() {
    return assertObjectPayload(
      await httpClient.requestJson(authBackendUrl('/api/operation-approvals/stats'), { method: 'GET' }),
      'operation_approval_stats_get'
    );
  },

  approveRequest(requestId, payload) {
    return httpClient.requestJson(
      authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/approve`),
      {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }
    );
  },

  rejectRequest(requestId, payload) {
    return httpClient.requestJson(
      authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/reject`),
      {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }
    );
  },

  withdrawRequest(requestId, payload = {}) {
    return httpClient.requestJson(
      authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/withdraw`),
      {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }
    );
  },

  async listInbox({ unreadOnly = false, limit = 100 } = {}) {
    return normalizeInboxPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/inbox${buildQuery({ unread_only: unreadOnly ? 'true' : '', limit })}`),
        { method: 'GET' }
      )
    );
  },

  markInboxRead(inboxId) {
    return httpClient.requestJson(authBackendUrl(`/api/inbox/${encodeURIComponent(inboxId)}/read`), {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  markAllInboxRead() {
    return httpClient.requestJson(authBackendUrl('/api/inbox/read-all'), {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },
};

export default operationApprovalApi;
