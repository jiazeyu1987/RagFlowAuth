import { authBackendUrl } from '../../config/backend';

export const usersApiMethods = {
  async listUsers(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users?${queryParams}`),
      { method: 'GET' }
    );
  
    if (!response.ok) {
      throw new Error('Failed to list users');
    }
  
    return response.json();
  },

  async createUser(userData) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/users'),
      {
        method: 'POST',
        body: JSON.stringify(userData),
      }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create user');
    }
  
    return response.json();
  },

  async updateUser(userId, userData) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}`),
      {
        method: 'PUT',
        body: JSON.stringify(userData),
      }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update user');
    }
  
    return response.json();
  },

  async deleteUser(userId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}`),
      { method: 'DELETE' }
    );
  
    if (!response.ok) {
      throw new Error('Failed to delete user');
    }
  
    return response.json();
  },

  async resetPassword(userId, newPassword) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/password`),
      {
        method: 'PUT',
        body: JSON.stringify({ new_password: newPassword }),
      }
    );
  
    if (!response.ok) {
      throw new Error('Failed to reset password');
    }
  
    return response.json();
  },

  async getUserKnowledgeBases(userId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/kbs`),
      { method: 'GET' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get user KBs');
    }
  
    return response.json();  // { kb_ids: [...] }
  },

  async grantKnowledgeBaseAccess(userId, kbId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/kbs/${encodeURIComponent(kbId)}`),
      { method: 'POST' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to grant KB access');
    }
  
    return response.json();
  },

  async revokeKnowledgeBaseAccess(userId, kbId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/kbs/${encodeURIComponent(kbId)}`),
      { method: 'DELETE' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to revoke KB access');
    }
  
    return response.json();
  },

  async batchGrantKnowledgeBases(userIds, kbIds) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/users/batch-grant'),
      {
        method: 'POST',
        body: JSON.stringify({ user_ids: userIds, kb_ids: kbIds })
      }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to batch grant');
    }
  
    return response.json();
  },

  async getUserChats(userId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/chats`),
      { method: 'GET' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get user chats');
    }
  
    return response.json();  // { chat_ids: [...] }
  },

  async grantChatAccess(userId, chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/chats/${encodeURIComponent(chatId)}`),
      { method: 'POST' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to grant chat access');
    }
  
    return response.json();
  },

  async revokeChatAccess(userId, chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/chats/${encodeURIComponent(chatId)}`),
      { method: 'DELETE' }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to revoke chat access');
    }
  
    return response.json();
  },

  async batchGrantChats(userIds, chatIds) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/users/batch-grant-chats'),
      {
        method: 'POST',
        body: JSON.stringify({ user_ids: userIds, chat_ids: chatIds })
      }
    );
  
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to batch grant chats');
    }
  
    return response.json();
  },
};
