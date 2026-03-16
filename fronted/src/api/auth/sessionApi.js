import { authBackendUrl } from '../../config/backend';

export const sessionApiMethods = {
  async listMyChats() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/chats/my'),
      { method: 'GET' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取我的对话失败'));
    }
  
    return response.json();  // { chat_ids: [...] }
  },

  async getChat(chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}`),
      { method: 'GET' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取对话失败'));
    }
  
    return response.json();
  },

  async createChatSession(chatId, name = '新会话') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}/sessions`),
      {
        method: 'POST',
        body: JSON.stringify({ name })
      }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '创建会话失败'));
    }
  
    return response.json();
  },

  async listChatSessions(chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}/sessions`),
      { method: 'GET' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取会话列表失败'));
    }
  
    return response.json();
  },

  async deleteChatSessions(chatId, sessionIds = null) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}/sessions`),
      {
        method: 'DELETE',
        body: JSON.stringify(sessionIds ? { ids: sessionIds } : {})
      }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '删除会话失败'));
    }
  
    return response.json();
  },

  async getMyChats() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/me/chats'),
      { method: 'GET' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取我的对话失败'));
    }
  
    return response.json();  // { chat_ids: [...] }
  },

  createAgentCompletionStream(agentId, question, sessionId = null) {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('未找到访问令牌');
    }
  
    const url = new URL(authBackendUrl(`/api/agents/${agentId}/completions`));
    url.searchParams.append('question', question);
    if (sessionId) {
      url.searchParams.append('session_id', sessionId);
    }
  
    return new EventSource(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
  },
};
