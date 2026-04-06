import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const normalizeKnowledgeBases = (response) => {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error('me_kbs_invalid_payload');
  }
  const payload = response.kbs;
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('me_kbs_invalid_payload');
  }
  if (!Array.isArray(payload.kb_ids) || !Array.isArray(payload.kb_names)) {
    throw new Error('me_kbs_invalid_payload');
  }
  return {
    kbIds: payload.kb_ids,
    kbNames: payload.kb_names,
  };
};

const normalizeResultMessage = (response, action) => {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error(`${action}_invalid_payload`);
  }
  const result = response.result;
  if (!result || typeof result !== 'object' || Array.isArray(result)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof result.message !== 'string' || !result.message.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return {
    message: result.message,
  };
};

export const meApi = {
  async listMyKnowledgeBases() {
    const response = await httpClient.requestJson(authBackendUrl('/api/me/kbs'), { method: 'GET' });
    return normalizeKnowledgeBases(response);
  },

  async changePassword(oldPassword, newPassword) {
    const response = await httpClient.requestJson(authBackendUrl('/api/auth/password'), {
      method: 'PUT',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
      }),
    });
    return normalizeResultMessage(response, 'me_change_password');
  },
};

export default meApi;
