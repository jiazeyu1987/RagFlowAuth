import { authBackendUrl } from '../../../config/backend';
import { httpClient } from '../../../shared/http/httpClient';

function assertOkResponse(response, action) {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!response.result || typeof response.result !== 'object' || Array.isArray(response.result)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof response.result.message !== 'string' || !response.result.message.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return response.result;
}

function normalizeConfigEnvelope(response, action) {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!response.config || typeof response.config !== 'object' || Array.isArray(response.config)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return response.config;
}

export const searchConfigsApi = {
  async listConfigs() {
    const response = await httpClient.requestJson(authBackendUrl('/api/search/configs'), { method: 'GET' });
    if (!Array.isArray(response?.configs)) {
      throw new Error('search_config_list_invalid_payload');
    }
    return response.configs;
  },

  async getConfig(configId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'GET',
    });
    return normalizeConfigEnvelope(response, 'search_config_get');
  },

  async createConfig(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/search/configs'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return normalizeConfigEnvelope(response, 'search_config_create');
  },

  async updateConfig(configId, updates) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'PUT',
      body: JSON.stringify(updates || {}),
    });
    return normalizeConfigEnvelope(response, 'search_config_update');
  },

  async deleteConfig(configId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'DELETE',
    });
    return assertOkResponse(response, 'search_config_delete');
  },
};
