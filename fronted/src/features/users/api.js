import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const usersApi = {
  list(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/users?${query}` : '/api/users';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },

  async items(params = {}) {
    const response = await this.list(params);
    if (Array.isArray(response)) return response;
    if (Array.isArray(response?.items)) return response.items;
    if (Array.isArray(response?.users)) return response.users;
    return [];
  },

  search(keyword, limit = 20) {
    return this.items({ q: keyword, limit });
  },

  create(payload) {
    return httpClient.requestJson(authBackendUrl('/api/users'), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update(userId, payload) {
    return httpClient.requestJson(authBackendUrl(`/api/users/${userId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  remove(userId) {
    return httpClient.requestJson(authBackendUrl(`/api/users/${userId}`), {
      method: 'DELETE',
    });
  },

  resetPassword(userId, newPassword) {
    return httpClient.requestJson(authBackendUrl(`/api/users/${userId}/password`), {
      method: 'PUT',
      body: JSON.stringify({ new_password: newPassword }),
    });
  },
};
