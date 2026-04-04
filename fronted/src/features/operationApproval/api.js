import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

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
  listWorkflows() {
    return httpClient.requestJson(authBackendUrl('/api/operation-approvals/workflows'), { method: 'GET' });
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

  listRequests({ view = 'mine', status = 'all', limit = 100 } = {}) {
    return httpClient.requestJson(
      authBackendUrl(
        `/api/operation-approvals/requests${buildQuery({
          view,
          status: status && status !== 'all' ? status : '',
          limit,
        })}`
      ),
      { method: 'GET' }
    );
  },

  listTodos({ limit = 100 } = {}) {
    return httpClient.requestJson(
      authBackendUrl(`/api/operation-approvals/todos${buildQuery({ limit })}`),
      { method: 'GET' }
    );
  },

  getRequest(requestId) {
    return httpClient.requestJson(
      authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}`),
      { method: 'GET' }
    );
  },

  getStats() {
    return httpClient.requestJson(authBackendUrl('/api/operation-approvals/stats'), { method: 'GET' });
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

  listInbox({ unreadOnly = false, limit = 100 } = {}) {
    return httpClient.requestJson(
      authBackendUrl(`/api/inbox${buildQuery({ unread_only: unreadOnly ? 'true' : '', limit })}`),
      { method: 'GET' }
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
