import { authBackendUrl } from '../../../config/backend';
import { httpClient } from '../../../shared/http/httpClient';

function assertOkResponse(response, action) {
  if (response?.ok !== true) {
    const detail = String(response?.detail || response?.error || '').trim();
    throw new Error(detail || `${action}_failed`);
  }
}

function unwrapEnvelope(response) {
  if (!response || typeof response !== 'object') return response;
  if (response.config && typeof response.config === 'object') return response.config;
  if (response.data?.config && typeof response.data.config === 'object') return response.data.config;
  return response;
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
    return unwrapEnvelope(response);
  },

  async createConfig(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/search/configs'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return unwrapEnvelope(response);
  },

  async updateConfig(configId, updates) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'PUT',
      body: JSON.stringify(updates || {}),
    });
    return unwrapEnvelope(response);
  },

  async deleteConfig(configId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/search/configs/${encodeURIComponent(configId)}`), {
      method: 'DELETE',
    });
    assertOkResponse(response, 'search_config_delete');
  },
};

