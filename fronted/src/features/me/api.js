import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const meApi = {
  listMyKnowledgeBases() {
    return httpClient.requestJson(authBackendUrl('/api/me/kbs'), { method: 'GET' });
  },

  changePassword(oldPassword, newPassword) {
    return httpClient.requestJson(authBackendUrl('/api/auth/password'), {
      method: 'PUT',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
      }),
    });
  },
};

export default meApi;
