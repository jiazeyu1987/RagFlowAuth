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
  runFullBackup: async () =>
    httpClient.requestJson('/api/admin/data-security/backup/run-full', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  listJobs: async (limit = 30) =>
    httpClient.requestJson(`/api/admin/data-security/backup/jobs?limit=${encodeURIComponent(limit)}`),
  getJob: async (jobId) => httpClient.requestJson(`/api/admin/data-security/backup/jobs/${jobId}`),
  getEgressConfig: async () =>
    httpClient.requestJson('/api/admin/security/egress/config', {
      skipSessionRedirect: true,
    }),
  updateEgressConfig: async (payload) =>
    httpClient.requestJson('/api/admin/security/egress/config', {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    }),
  getFeatureFlags: async () => httpClient.requestJson('/api/admin/security/feature-flags'),
  updateFeatureFlags: async (payload) =>
    httpClient.requestJson('/api/admin/security/feature-flags', {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    }),
  rollbackDisableFeatureFlags: async () =>
    httpClient.requestJson('/api/admin/security/feature-flags/rollback-disable', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
};
