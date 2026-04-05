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
  if (response.chat && typeof response.chat === 'object') return response.chat;
  if (response.data?.chat && typeof response.data.chat === 'object') return response.data.chat;
  return response;
}

export const chatConfigsApi = {
  async listChats(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/chats?${query}` : '/api/chats';
    const response = await httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
    if (!Array.isArray(response?.chats)) {
      throw new Error('ragflow_chat_list_invalid_payload');
    }
    return response.chats;
  },

  async getChat(chatId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}`), {
      method: 'GET',
    });
    return unwrapEnvelope(response);
  },

  async createChat(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/chats'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return unwrapEnvelope(response);
  },

  async updateChat(chatId, updates) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}`), {
      method: 'PUT',
      body: JSON.stringify(updates || {}),
    });
    return unwrapEnvelope(response);
  },

  async deleteChat(chatId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}`), {
      method: 'DELETE',
    });
    assertOkResponse(response, 'ragflow_chat_delete');
  },

  async clearParsedFiles(chatId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}/clear-parsed-files`), {
      method: 'POST',
      body: JSON.stringify({}),
    });
    return unwrapEnvelope(response);
  },
};

