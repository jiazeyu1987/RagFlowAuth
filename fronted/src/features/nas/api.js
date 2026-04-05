import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const buildPathWithQuery = (path = '') => {
  const query = new URLSearchParams();
  if (path) {
    query.set('path', path);
  }
  const suffix = query.toString();
  return suffix ? `/api/nas/files?${suffix}` : '/api/nas/files';
};

export const nasApi = {
  listFiles(path = '') {
    return httpClient.requestJson(authBackendUrl(buildPathWithQuery(path)), {
      method: 'GET',
    });
  },

  importFolder(path, kbRef) {
    return httpClient.requestJson(authBackendUrl('/api/nas/import-folder'), {
      method: 'POST',
      body: JSON.stringify({ path, kb_ref: kbRef }),
    });
  },

  getFolderImportStatus(taskId) {
    return httpClient.requestJson(
      authBackendUrl(`/api/nas/import-folder/${encodeURIComponent(taskId)}`),
      { method: 'GET' }
    );
  },

  importFile(path, kbRef) {
    return httpClient.requestJson(authBackendUrl('/api/nas/import-file'), {
      method: 'POST',
      body: JSON.stringify({ path, kb_ref: kbRef }),
    });
  },
};

export default nasApi;
