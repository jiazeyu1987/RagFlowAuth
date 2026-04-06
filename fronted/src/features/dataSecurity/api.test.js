import { dataSecurityApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('dataSecurityApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('routes settings and backup actions through the auth backend base url', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ enabled: true, backup_target_path: '/app/data/backups' })
      .mockResolvedValueOnce({ enabled: false, replica_target_path: '/mnt/replica/RagflowAuth' })
      .mockResolvedValueOnce({ job_id: 101 })
      .mockResolvedValueOnce({ job_id: 102 });

    await expect(dataSecurityApi.getSettings()).resolves.toEqual({
      enabled: true,
      backup_target_path: '/app/data/backups',
      local_backup_target_path: '/app/data/backups',
      local_backup_pack_count: 0,
      windows_backup_target_path: '',
      windows_backup_pack_count: 0,
      windows_backup_pack_count_skipped: false,
    });
    await expect(dataSecurityApi.updateSettings({ enabled: false })).resolves.toEqual({
      enabled: false,
      replica_target_path: '/mnt/replica/RagflowAuth',
      local_backup_target_path: '',
      local_backup_pack_count: 0,
      windows_backup_target_path: '/mnt/replica/RagflowAuth',
      windows_backup_pack_count: 0,
      windows_backup_pack_count_skipped: false,
    });
    await expect(dataSecurityApi.runBackup()).resolves.toEqual({ job_id: 101 });
    await expect(dataSecurityApi.runFullBackup()).resolves.toEqual({ job_id: 102 });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/admin/data-security/settings'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/admin/data-security/settings',
      {
        method: 'PUT',
        body: JSON.stringify({ enabled: false }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/admin/data-security/backup/run',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/admin/data-security/backup/run-full',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
  });

  it('encodes path and query parameters for job and restore drill endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ jobs: [] })
      .mockResolvedValueOnce({ id: 'job/1' })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ drill_id: 'drill-1' });

    await expect(dataSecurityApi.listJobs('30&all=true')).resolves.toEqual({ jobs: [] });
    await expect(dataSecurityApi.getJob('job/1')).resolves.toEqual({ id: 'job/1' });
    await expect(dataSecurityApi.listRestoreDrills('20&kind=all')).resolves.toEqual({ items: [] });
    await expect(dataSecurityApi.createRestoreDrill({ job_id: 1 })).resolves.toEqual({ drill_id: 'drill-1' });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/admin/data-security/backup/jobs?limit=30%26all%3Dtrue'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/admin/data-security/backup/jobs/job%2F1'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/admin/data-security/restore-drills?limit=20%26kind%3Dall'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/admin/data-security/restore-drills',
      {
        method: 'POST',
        body: JSON.stringify({ job_id: 1 }),
      }
    );
  });
});
