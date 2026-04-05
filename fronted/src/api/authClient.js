import tokenStore from '../shared/auth/tokenStore';
import { authApiMethods } from './auth/authApi';

class AuthClient {
  constructor() {
    this.accessToken = tokenStore.getAccessToken();
    this.refreshToken = tokenStore.getRefreshToken();
    this.user = tokenStore.getUser();

    if (!this.accessToken) {
      this.user = null;
    }
  }

  setAuth(accessToken, refreshToken, user) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.user = user;
    tokenStore.setAuth(accessToken, refreshToken, user);
  }

  clearAuth() {
    this.accessToken = null;
    this.refreshToken = null;
    this.user = null;
    tokenStore.clearAuth();
  }
}

Object.assign(
  AuthClient.prototype,
  authApiMethods
);

const authClient = new AuthClient();
export default authClient;
