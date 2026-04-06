import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const normalizeObjectField = (response, fieldName, action) => {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error(`${action}_invalid_payload`);
  }
  const value = response[fieldName];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

export const chatApi = {
  async listMyChats() {
    const response = await httpClient.requestJson(authBackendUrl('/api/chats/my'), { method: 'GET' });
    if (!Array.isArray(response?.chats)) {
      throw new Error('chat_my_list_invalid_payload');
    }
    return response.chats;
  },

  async listChatSessions(chatId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions`), { method: 'GET' });
    if (!Array.isArray(response?.sessions)) {
      throw new Error('chat_session_list_invalid_payload');
    }
    return response.sessions;
  },

  async createChatSession(chatId, name = '\u65b0\u4f1a\u8bdd') {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions`), {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    return normalizeObjectField(response, 'session', 'chat_session_create');
  },

  async deleteChatSessions(chatId, ids) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions`), {
      method: 'DELETE',
      body: JSON.stringify({ ids }),
    });
    return normalizeObjectField(response, 'result', 'chat_session_delete');
  },

  async renameChatSession(chatId, sessionId, name) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions/${encodeURIComponent(sessionId)}`), {
      method: 'PUT',
      body: JSON.stringify({ name }),
    });
    return normalizeObjectField(response, 'session', 'chat_session_rename');
  },

  requestCompletionStream(chatId, { question, sessionId, traceId } = {}) {
    return httpClient.request(authBackendUrl(`/api/chats/${chatId}/completions`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Chat-Trace-Id': traceId,
      },
      body: JSON.stringify({
        question,
        stream: true,
        session_id: sessionId,
      }),
    });
  },
};
