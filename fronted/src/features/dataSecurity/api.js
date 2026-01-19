import { httpClient } from '../../shared/http/httpClient';

export const dataSecurityApi = {
  getSettings: async () => httpClient.requestJson('/api/admin/data-security/settings'),
  updateSettings: async (settings) =>
    httpClient.requestJson('/api/admin/data-security/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),
  runBackup: async () =>
    httpClient.requestJson('/api/admin/data-security/backup/run', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  listJobs: async (limit = 30) =>
    httpClient.requestJson(`/api/admin/data-security/backup/jobs?limit=${encodeURIComponent(limit)}`),
  getJob: async (jobId) => httpClient.requestJson(`/api/admin/data-security/backup/jobs/${jobId}`),
};

