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

const normalizeWorkflowUpdateResult = (payload) => {
  const result = normalizeResultEnvelope(payload, 'operation_approval_workflow_update');
  if (typeof result.operation_type !== 'string' || !result.operation_type.trim()) {
    throw new Error('operation_approval_workflow_update_invalid_payload');
  }
  return result;
};

const normalizeRequestActionResult = (payload, action) => {
  const result = normalizeResultEnvelope(payload, action);
  if (typeof result.request_id !== 'string' || !result.request_id.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof result.status !== 'string' || !result.status.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return result;
};

const normalizeInboxReadResult = (payload) => {
  const result = normalizeResultEnvelope(payload, 'operation_approval_inbox_read');
  if (typeof result.inbox_id !== 'string' || !result.inbox_id.trim()) {
    throw new Error('operation_approval_inbox_read_invalid_payload');
  }
  if (typeof result.status !== 'string' || !result.status.trim()) {
    throw new Error('operation_approval_inbox_read_invalid_payload');
  }
  return result;
};

const normalizeInboxMarkAllResult = (payload) => {
  const result = normalizeResultEnvelope(payload, 'operation_approval_inbox_read_all');
  if (!Number.isInteger(result.updated) || result.updated < 0) {
    throw new Error('operation_approval_inbox_read_all_invalid_payload');
  }
  if (!Number.isInteger(result.unread_count) || result.unread_count < 0) {
    throw new Error('operation_approval_inbox_read_all_invalid_payload');
  }
  return result;
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

export const operationApprovalApi = {
  async listWorkflows() {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/operation-approvals/workflows'), { method: 'GET' }),
      'items',
      'operation_approval_workflows_list'
    );
  },

  async updateWorkflow(operationType, payload) {
    return normalizeWorkflowUpdateResult(
      await httpClient.requestJson(
        authBackendUrl(`/api/operation-approvals/workflows/${encodeURIComponent(operationType)}`),
        {
          method: 'PUT',
          body: JSON.stringify(payload || {}),
        }
      )
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

  async approveRequest(requestId, payload) {
    return normalizeRequestActionResult(
      await httpClient.requestJson(
        authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/approve`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'operation_approval_request_approve'
    );
  },

  async rejectRequest(requestId, payload) {
    return normalizeRequestActionResult(
      await httpClient.requestJson(
        authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/reject`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'operation_approval_request_reject'
    );
  },

  async withdrawRequest(requestId, payload = {}) {
    return normalizeRequestActionResult(
      await httpClient.requestJson(
        authBackendUrl(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/withdraw`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'operation_approval_request_withdraw'
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

  async markInboxRead(inboxId) {
    return normalizeInboxReadResult(
      await httpClient.requestJson(authBackendUrl(`/api/inbox/${encodeURIComponent(inboxId)}/read`), {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );
  },

  async markAllInboxRead() {
    return normalizeInboxMarkAllResult(
      await httpClient.requestJson(authBackendUrl('/api/inbox/read-all'), {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );
  },
};

export default operationApprovalApi;
