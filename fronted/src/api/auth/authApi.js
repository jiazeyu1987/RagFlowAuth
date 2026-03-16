import { authBackendUrl } from '../../config/backend';
import tokenStore from '../../shared/auth/tokenStore';
import { httpClient } from './httpClient';

export const authApiMethods = {
  normalizeDisplayError(message, fallback = '请求失败') {
    const text = String(message || '').trim();
    if (!text) return fallback;
    // 页面不直接显示英文后端错误，统一回退中文提示。
    if (/[\u4e00-\u9fff]/.test(text)) return text;
    return fallback;
  },

  resolveErrorMessage(errorPayload, fallback = '请求失败') {
    const detail =
      (typeof errorPayload?.detail === 'string' && errorPayload.detail) ||
      (typeof errorPayload?.message === 'string' && errorPayload.message) ||
      (typeof errorPayload?.error === 'string' && errorPayload.error) ||
      '';
    return this.normalizeDisplayError(detail, fallback);
  },

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
  
    // 存储访问令牌与刷新令牌
    this.setAuth(data.access_token, data.refresh_token, user);
  
    return {
      ...data,
      user  // 兼容历史调用
    };
  },

  async logout() {
    try {
      await httpClient.requestJson(authBackendUrl('/api/auth/logout'), {
        method: 'POST',
        skipRefresh: true,
      });
    } catch (error) {
      console.error('退出登录失败：', error);
    } finally {
      this.clearAuth();
    }
  },

  async getCurrentUser() {
    const response = await this.fetchWithAuth(authBackendUrl('/api/auth/me'), {
      method: 'GET',
    });
  
    if (!response.ok) {
      throw new Error('获取当前用户失败');
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
      let errorMessage = '修改密码失败';
      try {
        const data = await response.json();
        errorMessage = this.resolveErrorMessage(data, '修改密码失败');
      } catch {
        // ignore
      }
      throw new Error(errorMessage);
    }
  
    return response.json();
  },
};
