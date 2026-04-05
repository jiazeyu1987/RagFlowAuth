import tokenStore from '../shared/auth/tokenStore';
import authApi from './auth/authApi';

const authClient = {
  get accessToken() {
    return tokenStore.getAccessToken();
  },

  set accessToken(token) {
    tokenStore.setAccessToken(token);
  },

  get refreshToken() {
    return tokenStore.getRefreshToken();
  },

  set refreshToken(token) {
    tokenStore.setRefreshToken(token);
  },

  get user() {
    return this.accessToken ? tokenStore.getUser() : null;
  },

  set user(user) {
    tokenStore.setUser(user);
  },

  setAuth(accessToken, refreshToken, user) {
    tokenStore.setAuth(accessToken, refreshToken, user);
  },

  clearAuth() {
    tokenStore.clearAuth();
  },

  async refreshAccessToken() {
    try {
      return await authApi.refreshAccessToken();
    } catch (error) {
      this.clearAuth();
      window.location.href = '/login';
      throw error;
    }
  },

  fetchWithAuth(url, options = {}) {
    return authApi.fetchWithAuth(url, options);
  },

  async login(username, password) {
    const data = await authApi.login(username, password);
    this.setAuth(data.access_token, data.refresh_token, data.user);
    return data;
  },

  async logout() {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearAuth();
    }
  },

  async getCurrentUser() {
    const user = await authApi.getCurrentUser();
    this.user = user;
    return user;
  },
};

export default authClient;
