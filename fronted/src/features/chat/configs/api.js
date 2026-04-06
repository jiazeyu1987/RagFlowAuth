import { authBackendUrl } from '../../../config/backend';
import { httpClient } from '../../../shared/http/httpClient';

function assertOkResponse(response, action) {
  if (response?.ok !== true) {
    const detail = String(response?.detail || response?.error || '').trim();
    throw new Error(detail || `${action}_failed`);
  }
}

function normalizeChatEnvelope(response, action) {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!response.chat || typeof response.chat !== 'object' || Array.isArray(response.chat)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return response.chat;
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
    return normalizeChatEnvelope(response, 'ragflow_chat_get');
  },

  async createChat(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/chats'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return normalizeChatEnvelope(response, 'ragflow_chat_create');
  },

  async updateChat(chatId, updates) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${encodeURIComponent(chatId)}`), {
      method: 'PUT',
      body: JSON.stringify(updates || {}),
    });
    return normalizeChatEnvelope(response, 'ragflow_chat_update');
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
    return normalizeChatEnvelope(response, 'ragflow_chat_clear_parsed_files');
  },
};
