import { authBackendUrl } from '../../config/backend';
import tokenStore from '../../shared/auth/tokenStore';
import { httpClient } from './httpClient';

export const authApiMethods = {
  async refreshAccessToken() {
    try {
      const token = await httpClient.refreshAccessToken();
      this.accessToken = token;
      this.refreshToken = tokenStore.getRefreshToken();
      return token;
    } catch (e) {
      this.clearAuth();
      window.location.href = '/login';
      throw e;
    }
  },

  async fetchWithAuth(url, options = {}) {
    const response = await httpClient.request(url, options);
    this.accessToken = tokenStore.getAccessToken();
    this.refreshToken = tokenStore.getRefreshToken();
    this.user = tokenStore.getUser();
    return response;
  },

  async login(username, password) {
    const data = await httpClient.requestJson(authBackendUrl('/api/auth/login'), {
      method: 'POST',
      skipAuth: true,
      skipRefresh: true,
      body: JSON.stringify({ username, password }),
    });
  
    const user = await httpClient.requestJson(authBackendUrl('/api/auth/me'), {
      headers: { 'Authorization': `Bearer ${data.access_token}` },
      skipRefresh: true,
    });
  
    // 瀛樺偍涓ょ浠ょ墝
    this.setAuth(data.access_token, data.refresh_token, user);
  
    return {
      ...data,
      user  // 涓轰簡鍏煎鏃т唬鐮?
    };
  },

  async logout() {
    try {
      await httpClient.requestJson(authBackendUrl('/api/auth/logout'), {
        method: 'POST',
        skipRefresh: true,
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearAuth();
    }
  },

  async getCurrentUser() {
    const response = await this.fetchWithAuth(authBackendUrl('/api/auth/me'), {
      method: 'GET',
    });
  
    if (!response.ok) {
      throw new Error('Failed to get current user');
    }
  
    return response.json();
  },

  async changePassword(oldPassword, newPassword) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/auth/password'),
      {
        method: 'PUT',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      }
    );
  
    if (!response.ok) {
      let errorMessage = 'Failed to change password';
      try {
        const data = await response.json();
        if (data?.detail) errorMessage = data.detail;
      } catch {
        // ignore
      }
      throw new Error(errorMessage);
    }
  
    return response.json();
  },
};
