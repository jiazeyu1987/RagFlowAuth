import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const normalizeResultEnvelope = (payload, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!envelope.result || typeof envelope.result !== 'object' || Array.isArray(envelope.result)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof envelope.result.message !== 'string' || !envelope.result.message.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope.result;
};

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

  async logout() {
    return normalizeResultEnvelope(
      await httpClient.requestJson(authBackendUrl('/api/auth/logout'), {
        method: 'POST',
        skipRefresh: true,
      }),
      'auth_logout'
    );
  },

  getCurrentUser(options = {}) {
    return httpClient.requestJson(authBackendUrl('/api/auth/me'), {
      method: 'GET',
      ...options,
    });
  },
};

export default authApi;
