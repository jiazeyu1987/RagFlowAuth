import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertArrayPayload = (payload, action) => {
  if (!Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const normalizeObjectField = (response, fieldName, action) => {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error(`${action}_invalid_payload`);
  }
  const value = response[fieldName];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

const requestUsersList = async (params = {}, action = 'users_list') => {
  const query = new URLSearchParams(params).toString();
  const path = query ? `/api/users?${query}` : '/api/users';
  return assertArrayPayload(
    await httpClient.requestJson(authBackendUrl(path), { method: 'GET' }),
    action
  );
};

export const usersApi = {
  list(params = {}) {
    return requestUsersList(params, 'users_list');
  },

  items(params = {}) {
    return requestUsersList(params, 'users_items');
  },

  search(keyword, limit = 20) {
    return requestUsersList({ q: keyword, limit }, 'users_search');
  },

  async get(userId) {
    return assertObjectPayload(
      await httpClient.requestJson(authBackendUrl(`/api/users/${userId}`), {
        method: 'GET',
      }),
      'users_get'
    );
  },

  async create(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/users'), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return normalizeObjectField(response, 'user', 'users_create');
  },

  async update(userId, payload) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/users/${userId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    return normalizeObjectField(response, 'user', 'users_update');
  },

  async remove(userId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/users/${userId}`), {
      method: 'DELETE',
    });
    return normalizeObjectField(response, 'result', 'users_remove');
  },

  async resetPassword(userId, newPassword) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/users/${userId}/password`), {
      method: 'PUT',
      body: JSON.stringify({ new_password: newPassword }),
    });
    return normalizeObjectField(response, 'result', 'users_reset_password');
  },
};
