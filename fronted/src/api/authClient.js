import tokenStore from '../shared/auth/tokenStore';
import authApi from './auth/authApi';

const syncFromStore = (client) => {
  client.accessToken = tokenStore.getAccessToken();
  client.refreshToken = tokenStore.getRefreshToken();
  client.user = client.accessToken ? tokenStore.getUser() : null;
  return client;
};

const authClient = {
  accessToken: null,
  refreshToken: null,
  user: null,

  setAuth(accessToken, refreshToken, user) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.user = user;
    tokenStore.setAuth(accessToken, refreshToken, user);
  },

  clearAuth() {
    this.accessToken = null;
    this.refreshToken = null;
    this.user = null;
    tokenStore.clearAuth();
  },

  async refreshAccessToken() {
    try {
      const token = await authApi.refreshAccessToken();
      syncFromStore(this);
      return token;
    } catch (error) {
      this.clearAuth();
      window.location.href = '/login';
      throw error;
    }
  },

  async fetchWithAuth(url, options = {}) {
    const response = await authApi.fetchWithAuth(url, options);
    syncFromStore(this);
    return response;
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
    syncFromStore(this);
    return user;
  },
};

syncFromStore(authClient);

export default authClient;
