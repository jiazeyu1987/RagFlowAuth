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

const metrologyApi = {
  async listRecords(filters = {}) {
    return ensureArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/metrology/records${buildQuery({
            limit: filters.limit ?? 100,
            equipment_id: filters.equipmentId,
            status: filters.status,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'metrology_records_list'
    );
  },

  async createRecord(payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl('/api/metrology/records'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'metrology_record_create'
    );
  },

  async recordResult(recordId, payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/metrology/records/${recordId}/record`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'metrology_record_record'
    );
  },

  async confirmRecord(recordId, payload = {}) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/metrology/records/${recordId}/confirm`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'metrology_record_confirm'
    );
  },

  async approveRecord(recordId, payload = {}) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/metrology/records/${recordId}/approve`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'metrology_record_approve'
    );
  },

  async dispatchReminders(windowDays = 7) {
    return ensureObject(
      await httpClient.requestJson(
        authBackendUrl(`/api/metrology/reminders/dispatch${buildQuery({ window_days: windowDays })}`),
        { method: 'POST' }
      ),
      'metrology_reminder_dispatch'
    );
  },
};

export default metrologyApi;
