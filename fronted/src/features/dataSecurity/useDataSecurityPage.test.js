import { act, renderHook, waitFor } from '@testing-library/react';
import useDataSecurityPage from './useDataSecurityPage';
import { dataSecurityApi } from './api';

jest.mock('./api', () => ({
  dataSecurityApi: {
    getSettings: jest.fn(),
    updateSettings: jest.fn(),
    runBackup: jest.fn(),
    runFullBackup: jest.fn(),
    listJobs: jest.fn(),
    getJob: jest.fn(),
    listRestoreDrills: jest.fn(),
    createRestoreDrill: jest.fn(),
    runRealRestore: jest.fn(),
  },
}));

const settingsResponse = {
  enabled: true,
  backup_retention_max: 7,
  local_backup_target_path: '/app/data/backups',
  incremental_schedule: '30 18 * * *',
  full_backup_enabled: true,
  full_backup_schedule: '0 2 * * 1',
  ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
  ragflow_stop_services: false,
  full_backup_include_images: true,
  auth_db_path: 'data/auth.db',
};

const createJob = (overrides = {}) => ({
  id: 101,
  kind: 'incremental',
  status: 'completed',
  message: '备份完成',
  progress: 100,
  package_hash: 'hash-local-101',
  output_dir: '/app/data/backups/migration_pack_20260404_120000',
  created_at_ms: 1_775_270_400_000,
  started_at_ms: 1_775_270_300_000,
  detail: '',
  ...overrides,
});

describe('useDataSecurityPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    dataSecurityApi.getSettings.mockResolvedValue(settingsResponse);
    dataSecurityApi.updateSettings.mockResolvedValue(settingsResponse);
    dataSecurityApi.listJobs.mockResolvedValue([createJob()]);
    dataSecurityApi.listRestoreDrills.mockResolvedValue([]);
    dataSecurityApi.createRestoreDrill.mockResolvedValue({
      drill_id: 'drill-1',
      job_id: 101,
      result: 'passed',
    });
    dataSecurityApi.runRealRestore.mockResolvedValue({
      job_id: 101,
      result: 'success',
      live_auth_db_path: '/app/data/auth.db',
    });
  });

  it('loads settings, jobs, and restore options into stable hook state', async () => {
    const { result } = renderHook(() => useDataSecurityPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(dataSecurityApi.getSettings).toHaveBeenCalledTimes(1);
    expect(dataSecurityApi.listJobs).toHaveBeenCalledWith(30);
    expect(dataSecurityApi.listRestoreDrills).toHaveBeenCalledWith(30);
    expect(result.current.localBackupTargetPath).toBe('/app/data/backups');
    expect(result.current.restoreEligibleJobs).toHaveLength(1);
    expect(result.current.selectedRestoreJobId).toBe('101');
    expect(result.current.canSubmitRestoreDrill).toBe(true);
    expect(result.current.canSubmitRealRestore).toBe(true);
    expect(result.current.restoreDrillBlockedReason).toBe('');
    expect('windowsBackupTargetPath' in result.current).toBe(false);
  });

  it('submits restore drills through the feature api using the selected local backup', async () => {
    const { result } = renderHook(() => useDataSecurityPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      result.current.setRestoreTarget('qa-staging');
      result.current.setRestoreNotes('local-only drill');
    });

    await act(async () => {
      await result.current.submitRestoreDrill();
    });

    expect(dataSecurityApi.createRestoreDrill).toHaveBeenCalledWith({
      job_id: 101,
      backup_path: '/app/data/backups/migration_pack_20260404_120000',
      backup_hash: 'hash-local-101',
      restore_target: 'qa-staging',
      verification_notes: 'local-only drill',
    });
  });

  it('submits real restore through the feature api using the selected local backup', async () => {
    const { result } = renderHook(() => useDataSecurityPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    let response = null;
    await act(async () => {
      response = await result.current.submitRealRestore({
        changeReason: 'recover deleted user',
        confirmationText: 'RESTORE',
      });
    });

    expect(dataSecurityApi.runRealRestore).toHaveBeenCalledWith({
      job_id: 101,
      backup_path: '/app/data/backups/migration_pack_20260404_120000',
      backup_hash: 'hash-local-101',
      change_reason: 'recover deleted user',
      confirmation_text: 'RESTORE',
    });
    expect(response).toEqual({
      job_id: 101,
      result: 'success',
      live_auth_db_path: '/app/data/auth.db',
    });
  });

  it('exposes a blocked reason when no local backup job can be used for restore drills', async () => {
    dataSecurityApi.listJobs.mockResolvedValue([
      createJob({
        id: 301,
        output_dir: '',
        package_hash: 'hash-local-301',
      }),
    ]);

    const { result } = renderHook(() => useDataSecurityPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.canSubmitRestoreDrill).toBe(false);
    expect(result.current.canSubmitRealRestore).toBe(false);
    expect(result.current.restoreDrillBlockedReason).toContain(
      '当前没有可用于恢复的服务器本机备份任务'
    );
  });

  it('saves only generic backup settings without Windows replica fields', async () => {
    const { result } = renderHook(() => useDataSecurityPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      result.current.setSettingField('enabled', false);
      result.current.setSettingField('incremental_schedule', '15 23 * * 3');
      result.current.setSettingField('full_backup_enabled', false);
      result.current.setSettingField('full_backup_schedule', '0 3 * * 6');
      result.current.setSettingField('ragflow_compose_path', '/srv/ragflow/docker-compose.yml');
      result.current.setSettingField('ragflow_stop_services', true);
      result.current.setSettingField('full_backup_include_images', false);
      result.current.setSettingField('auth_db_path', 'config/auth.db');
    });

    await act(async () => {
      await result.current.saveSettings('update local backup settings');
    });

    expect(dataSecurityApi.updateSettings).toHaveBeenCalledWith({
      enabled: false,
      incremental_schedule: '15 23 * * 3',
      full_backup_enabled: false,
      full_backup_schedule: '0 3 * * 6',
      ragflow_compose_path: '/srv/ragflow/docker-compose.yml',
      ragflow_stop_services: true,
      auth_db_path: 'config/auth.db',
      full_backup_include_images: false,
      change_reason: 'update local backup settings',
    });
  });
});
