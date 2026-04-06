import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const authApi = {
  refreshAccessToken() {
    return httpClient.refreshAccessToken();
  },

  async login(username, password) {
    const data = await httpClient.requestJson(authBackendUrl('/api/auth/login'), {
      method: 'POST',
      skipAuth: true,
      skipRefresh: true,
      body: JSON.stringify({ username, password }),
    });

    const user = await httpClient.requestJson(authBackendUrl('/api/auth/me'), {
      headers: { Authorization: `Bearer ${data.access_token}` },
      skipRefresh: true,
    });

    return {
      ...data,
      user,
    };
  },

  logout() {
    return httpClient.requestJson(authBackendUrl('/api/auth/logout'), {
      method: 'POST',
      skipRefresh: true,
    });
  },

  getCurrentUser(options = {}) {
    return httpClient.requestJson(authBackendUrl('/api/auth/me'), {
      method: 'GET',
      ...options,
    });
  },
};

export default authApi;
