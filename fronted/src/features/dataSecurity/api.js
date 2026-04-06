import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const normalizeSettings = (payload) => {
  const data = payload && typeof payload === 'object' ? payload : {};
  return {
    ...data,
    local_backup_target_path: String(data.local_backup_target_path || ''),
    local_backup_pack_count: Number(data.local_backup_pack_count ?? 0) || 0,
    windows_backup_target_path: String(data.windows_backup_target_path || ''),
    windows_backup_pack_count: Number(data.windows_backup_pack_count ?? 0) || 0,
    windows_backup_pack_count_skipped: Boolean(data.windows_backup_pack_count_skipped),
  };
};

export const dataSecurityApi = {
  getSettings: async () =>
    normalizeSettings(await httpClient.requestJson(authBackendUrl('/api/admin/data-security/settings'))),

  updateSettings: async (settings) =>
    normalizeSettings(
      await httpClient.requestJson(authBackendUrl('/api/admin/data-security/settings'), {
        method: 'PUT',
        body: JSON.stringify(settings),
      })
    ),

  runBackup: async () =>
    httpClient.requestJson(authBackendUrl('/api/admin/data-security/backup/run'), {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  runFullBackup: async () =>
    httpClient.requestJson(authBackendUrl('/api/admin/data-security/backup/run-full'), {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  listJobs: async (limit = 30) =>
    httpClient.requestJson(
      authBackendUrl(`/api/admin/data-security/backup/jobs?limit=${encodeURIComponent(limit)}`)
    ),

  getJob: async (jobId) =>
    httpClient.requestJson(
      authBackendUrl(`/api/admin/data-security/backup/jobs/${encodeURIComponent(jobId)}`)
    ),

  listRestoreDrills: async (limit = 30) =>
    httpClient.requestJson(
      authBackendUrl(`/api/admin/data-security/restore-drills?limit=${encodeURIComponent(limit)}`)
    ),

  createRestoreDrill: async (payload) =>
    httpClient.requestJson(authBackendUrl('/api/admin/data-security/restore-drills'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }),
};
