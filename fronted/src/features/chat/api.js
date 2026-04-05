import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const chatApi = {
  listMyChats() {
    return httpClient.requestJson(authBackendUrl('/api/chats/my'), { method: 'GET' });
  },

  listChatSessions(chatId) {
    return httpClient.requestJson(authBackendUrl(`/api/chats/${chatId}/sessions`), { method: 'GET' });
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
