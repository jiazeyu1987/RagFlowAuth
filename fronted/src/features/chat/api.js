import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

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

  createChatSession(chatId, name = '新会话') {
    return httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions`), {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  deleteChatSessions(chatId, ids) {
    return httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions`), {
      method: 'DELETE',
      body: JSON.stringify({ ids }),
    });
  },

  renameChatSession(chatId, sessionId, name) {
    return httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions/${encodeURIComponent(sessionId)}`), {
      method: 'PUT',
      body: JSON.stringify({ name }),
    });
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
