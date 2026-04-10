import { useCallback, useEffect, useMemo, useState } from 'react';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import { dataSecurityApi } from './api';
import { getLocalBackupTargetPath } from './dataSecurityHelpers';
import useDataSecurityJobs from './useDataSecurityJobs';
import useRestoreDrillForm from './useRestoreDrillForm';

export default function useDataSecurityPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [settings, setSettings] = useState(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [savingRetention, setSavingRetention] = useState(false);

  const {
    jobs,
    restoreDrills,
    activeJob,
    running,
    refreshJobsAndDrills,
    loadJobsAndDrills,
    startPollingJob,
    handleSelectJob,
  } = useDataSecurityJobs();

  const restoreForm = useRestoreDrillForm({
    jobs,
    refreshJobsAndDrills,
    onError: setError,
  });

  const loadAll = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [settingsResponse] = await Promise.all([
        dataSecurityApi.getSettings(),
        loadJobsAndDrills(),
      ]);
      setSettings(settingsResponse);
    } catch (e) {
      setError(mapUserFacingErrorMessage(e?.message, '加载失败'));
    } finally {
      setLoading(false);
    }
  }, [loadJobsAndDrills]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const setSettingField = useCallback((field, value) => {
    setSettings((previous) => ({ ...(previous || {}), [field]: value }));
  }, []);

  const saveRetention = useCallback(
    async (changeReason) => {
      if (!settings) return false;
      const trimmedReason = String(changeReason || '').trim();
      if (!trimmedReason) {
        setError('变更原因不能为空');
        return false;
      }

      setError(null);
      setSavingRetention(true);
      try {
        const raw = Number(settings.backup_retention_max ?? 30);
        const clamped = Math.max(1, Math.min(100, Number.isFinite(raw) ? raw : 30));
        const response = await dataSecurityApi.updateSettings({
          backup_retention_max: clamped,
          change_reason: trimmedReason,
        });
        setSettings((previous) => ({ ...(previous || {}), ...(response || {}), backup_retention_max: clamped }));
        return true;
      } catch (e) {
        setError(mapUserFacingErrorMessage(e?.message, '保存失败'));
        return false;
      } finally {
        setSavingRetention(false);
      }
    },
    [settings]
  );

  const saveSettings = useCallback(
    async (changeReason) => {
      if (!settings) return false;
      const trimmedReason = String(changeReason || '').trim();
      if (!trimmedReason) {
        setError('变更原因不能为空');
        return false;
      }

      setError(null);
      setSavingSettings(true);
      try {
        const response = await dataSecurityApi.updateSettings({
          enabled: Boolean(settings.enabled),
          incremental_schedule: String(settings.incremental_schedule || '').trim() || null,
          full_backup_enabled: Boolean(settings.full_backup_enabled),
          full_backup_schedule: String(settings.full_backup_schedule || '').trim() || null,
          ragflow_compose_path: String(settings.ragflow_compose_path || '').trim(),
          ragflow_stop_services: Boolean(settings.ragflow_stop_services),
          auth_db_path: String(settings.auth_db_path || 'data/auth.db').trim(),
          full_backup_include_images: Boolean(settings.full_backup_include_images),
          change_reason: trimmedReason,
        });
        setSettings((previous) => ({ ...(previous || {}), ...(response || {}) }));
        return true;
      } catch (e) {
        setError(mapUserFacingErrorMessage(e?.message, '保存失败'));
        return false;
      } finally {
        setSavingSettings(false);
      }
    },
    [settings]
  );

  const runNow = useCallback(async () => {
    setError(null);
    try {
      const response = await dataSecurityApi.runBackup();
      if (response?.job_id) {
        await startPollingJob(response.job_id);
      }
    } catch (e) {
      setError(mapUserFacingErrorMessage(e?.message, '启动失败'));
    }
  }, [startPollingJob]);

  const runFullBackupNow = useCallback(async () => {
    setError(null);
    try {
      const response = await dataSecurityApi.runFullBackup();
      if (response?.job_id) {
        await startPollingJob(response.job_id);
      }
    } catch (e) {
      setError(mapUserFacingErrorMessage(e?.message, '全量备份启动失败'));
    }
  }, [startPollingJob]);

  const localBackupTargetPath = useMemo(() => getLocalBackupTargetPath(settings), [settings]);

  return {
    loading,
    running,
    error,
    settings,
    jobs,
    activeJob,
    savingSettings,
    savingRetention,
    restoreDrills,
    localBackupTargetPath,
    setSettingField,
    saveSettings,
    saveRetention,
    runNow,
    runFullBackupNow,
    handleSelectJob,
    ...restoreForm,
  };
}
