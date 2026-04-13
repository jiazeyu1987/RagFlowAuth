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

const changeControlApi = {
  async listRequests(filters = {}) {
    return ensureArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/change-control/requests${buildQuery({
            limit: filters.limit ?? 100,
            status: filters.status,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'change_control_requests_list'
    );
  },

  async getRequest(requestId) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}`), {
        method: 'GET',
      }),
      'change_control_request_get'
    );
  },

  async createRequest(payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl('/api/change-control/requests'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'change_control_request_create'
    );
  },

  async evaluateRequest(requestId, payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}/evaluate`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'change_control_request_evaluate'
    );
  },

  async createPlanItem(requestId, payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}/plan-items`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'change_control_plan_item_create'
    );
  },

  async updatePlanItemStatus(requestId, planItemId, payload) {
    return ensureObject(
      await httpClient.requestJson(
        authBackendUrl(`/api/change-control/requests/${requestId}/plan-items/${planItemId}`),
        {
          method: 'PATCH',
          body: JSON.stringify(payload || {}),
        }
      ),
      'change_control_plan_item_update'
    );
  },

  async markPlanned(requestId, payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}/plan`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'change_control_plan_mark'
    );
  },

  async startExecution(requestId) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}/start-execution`), {
        method: 'POST',
      }),
      'change_control_execution_start'
    );
  },

  async completeExecution(requestId, payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}/complete-execution`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'change_control_execution_complete'
    );
  },

  async confirmDepartment(requestId, payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}/confirmations`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'change_control_confirm_department'
    );
  },

  async dispatchReminders(windowDays = 7) {
    return ensureObject(
      await httpClient.requestJson(
        authBackendUrl(`/api/change-control/reminders/dispatch${buildQuery({ window_days: windowDays })}`),
        { method: 'POST' }
      ),
      'change_control_reminder_dispatch'
    );
  },

  async closeRequest(requestId, payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/change-control/requests/${requestId}/close`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'change_control_request_close'
    );
  },
};

export default changeControlApi;
