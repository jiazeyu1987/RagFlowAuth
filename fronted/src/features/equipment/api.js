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

const equipmentApi = {
  async listAssets(filters = {}) {
    return ensureArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/equipment/assets${buildQuery({
            limit: filters.limit ?? 100,
            status: filters.status,
            owner_user_id: filters.ownerUserId,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'equipment_assets_list'
    );
  },

  async getAsset(equipmentId) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/equipment/assets/by-id/${equipmentId}`), {
        method: 'GET',
      }),
      'equipment_asset_get'
    );
  },

  async createAsset(payload) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl('/api/equipment/assets'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'equipment_asset_create'
    );
  },

  async acceptAsset(equipmentId, payload = {}) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/equipment/assets/${equipmentId}/accept`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'equipment_asset_accept'
    );
  },

  async commissionAsset(equipmentId, payload = {}) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/equipment/assets/${equipmentId}/commission`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'equipment_asset_commission'
    );
  },

  async retireAsset(equipmentId, payload = {}) {
    return ensureObject(
      await httpClient.requestJson(authBackendUrl(`/api/equipment/assets/${equipmentId}/retire`), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'equipment_asset_retire'
    );
  },

  async dispatchReminders(windowDays = 7) {
    return ensureObject(
      await httpClient.requestJson(
        authBackendUrl(`/api/equipment/reminders/dispatch${buildQuery({ window_days: windowDays })}`),
        { method: 'POST' }
      ),
      'equipment_reminder_dispatch'
    );
  },
};

export default equipmentApi;
