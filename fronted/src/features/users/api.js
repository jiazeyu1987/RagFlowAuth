import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertArrayPayload = (payload, action) => {
  if (!Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
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
