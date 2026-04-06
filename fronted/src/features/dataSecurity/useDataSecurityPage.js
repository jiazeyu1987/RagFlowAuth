import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { dataSecurityApi } from './api';

const isRunningStatus = (status) => ['queued', 'running', 'canceling'].includes(String(status || '').toLowerCase());

export default function useDataSecurityPage() {
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [settings, setSettings] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
  const [savingRetention, setSavingRetention] = useState(false);
  const [restoreDrills, setRestoreDrills] = useState([]);
  const [selectedRestoreJobId, setSelectedRestoreJobId] = useState('');
  const [restoreTarget, setRestoreTarget] = useState('staging');
  const [restoreNotes, setRestoreNotes] = useState('');
  const [creatingRestoreDrill, setCreatingRestoreDrill] = useState(false);
  const pollTimer = useRef(null);

  const targetPreview = useMemo(() => {
    if (!settings) return '';
    if (settings.target_mode === 'local') return settings.target_local_dir || '';
    const ip = (settings.target_ip || '').trim();
    const share = (settings.target_share_name || '').trim().replace(/^\\\\+|\\\\+$/g, '').replace(/^\/+|\/+$/g, '');
    const sub = (settings.target_subdir || '').trim().replace(/^\\\\+|\\\\+$/g, '').replace(/^\/+|\/+$/g, '');
    if (!ip || !share) return '';
    return sub ? `\\\\${ip}\\${share}\\${sub}` : `\\\\${ip}\\${share}`;
  }, [settings]);

  const localBackupTargetPath = useMemo(() => settings?.local_backup_target_path || '', [settings]);

  const windowsBackupTargetPath = useMemo(
    () => settings?.windows_backup_target_path || targetPreview || '',
    [settings, targetPreview]
  );

  const restoreEligibleJobs = useMemo(
    () => (jobs || []).filter((job) => !!String(job?.output_dir || '').trim()),
    [jobs]
  );

  const selectedRestoreJob = useMemo(() => {
    const id = Number(selectedRestoreJobId);
    if (!Number.isFinite(id) || id <= 0) return null;
    return restoreEligibleJobs.find((item) => Number(item.id) === id) || null;
  }, [restoreEligibleJobs, selectedRestoreJobId]);

  const pickRestoreJobId = useCallback((nextJobs, prevValue = '') => {
    const eligible = (nextJobs || []).filter((job) => !!String(job?.output_dir || '').trim());
    if (prevValue && eligible.some((job) => String(job.id) === String(prevValue))) {
      return String(prevValue);
    }
    return eligible[0] ? String(eligible[0].id) : '';
  }, []);

  const refreshJobsAndDrills = useCallback(async () => {
    const [jobsResp, drillsResp] = await Promise.all([
      dataSecurityApi.listJobs(30),
      dataSecurityApi.listRestoreDrills(30),
    ]);
    const nextJobs = Array.isArray(jobsResp?.jobs) ? jobsResp.jobs : [];
    const nextDrills = Array.isArray(drillsResp?.items) ? drillsResp.items : [];
    setJobs(nextJobs);
    setRestoreDrills(nextDrills);
    setSelectedRestoreJobId((prev) => pickRestoreJobId(nextJobs, prev));
  }, [pickRestoreJobId]);

  const pollActiveJob = useCallback(async (jobId) => {
    try {
      const job = await dataSecurityApi.getJob(jobId);
      setActiveJob(job);
      const nextRunning = isRunningStatus(job?.status);
      setRunning(nextRunning);
      if (!nextRunning) {
        await refreshJobsAndDrills();
        if (pollTimer.current) {
          clearInterval(pollTimer.current);
          pollTimer.current = null;
        }
      }
      return nextRunning;
    } catch {
      return true;
    }
  }, [refreshJobsAndDrills]);

  const loadAll = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [settingsResp, jobsResp, drillsResp] = await Promise.all([
        dataSecurityApi.getSettings(),
        dataSecurityApi.listJobs(30),
        dataSecurityApi.listRestoreDrills(30),
      ]);
      const nextJobs = Array.isArray(jobsResp?.jobs) ? jobsResp.jobs : [];
      const nextDrills = Array.isArray(drillsResp?.items) ? drillsResp.items : [];
      const latest = nextJobs[0] || null;

      setSettings(settingsResp || {});
      setJobs(nextJobs);
      setRestoreDrills(nextDrills);
      setActiveJob(latest);
      setRunning(latest ? isRunningStatus(latest.status) : false);
      setSelectedRestoreJobId((prev) => pickRestoreJobId(nextJobs, prev));
    } catch (e) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [pickRestoreJobId]);

  useEffect(() => {
    loadAll();
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [loadAll]);

  const setSettingField = useCallback((field, value) => {
    setSettings((prev) => ({ ...(prev || {}), [field]: value }));
  }, []);

  const saveRetention = useCallback(async () => {
    if (!settings) return;
    const changeReason = window.prompt('请输入本次备份保留策略变更原因');
    if (changeReason === null) return;
    const trimmedReason = String(changeReason || '').trim();
    if (!trimmedReason) {
      setError('变更原因不能为空');
      return;
    }

    setError(null);
    setSavingRetention(true);
    try {
      const raw = Number(settings.backup_retention_max ?? 30);
      const clamped = Math.max(1, Math.min(100, Number.isFinite(raw) ? raw : 30));
      const resp = await dataSecurityApi.updateSettings({
        backup_retention_max: clamped,
        change_reason: trimmedReason,
      });
      setSettings((prev) => ({ ...(prev || {}), ...(resp || {}), backup_retention_max: clamped }));
    } catch (e) {
      setError(e.message || '保存失败');
    } finally {
      setSavingRetention(false);
    }
  }, [settings]);

  const startPollingJob = useCallback(async (jobId) => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    setRunning(true);
    const nextRunning = await pollActiveJob(jobId);
    if (nextRunning) {
      pollTimer.current = setInterval(() => {
        pollActiveJob(jobId);
      }, 1000);
    }
  }, [pollActiveJob]);

  const runNow = useCallback(async () => {
    setError(null);
    try {
      const res = await dataSecurityApi.runBackup();
      if (res?.job_id) await startPollingJob(res.job_id);
    } catch (e) {
      setError(e.message || '启动失败');
    }
  }, [startPollingJob]);

  const runFullBackupNow = useCallback(async () => {
    setError(null);
    try {
      const res = await dataSecurityApi.runFullBackup();
      if (res?.job_id) await startPollingJob(res.job_id);
    } catch (e) {
      setError(e.message || '全量备份启动失败');
    }
  }, [startPollingJob]);

  const handleSelectJob = useCallback((job) => {
    setActiveJob(job);
    if (job?.output_dir) {
      setSelectedRestoreJobId(String(job.id));
    }
    if (isRunningStatus(job?.status)) {
      setRunning(true);
      if (pollTimer.current) clearInterval(pollTimer.current);
      pollTimer.current = setInterval(() => {
        pollActiveJob(job.id);
      }, 1000);
    }
  }, [pollActiveJob]);

  const submitRestoreDrill = useCallback(async () => {
    setError(null);
    if (!selectedRestoreJob) {
      setError('请先选择可用于本地恢复演练的备份任务');
      return;
    }
    if (!selectedRestoreJob.output_dir) {
      setError('所选任务没有本地备份，无法执行恢复演练');
      return;
    }
    if (!selectedRestoreJob.package_hash) {
      setError('所选任务缺少 package_hash，无法执行恢复演练');
      return;
    }
    if (!restoreTarget.trim()) {
      setError('恢复目标不能为空');
      return;
    }

    setCreatingRestoreDrill(true);
    try {
      const created = await dataSecurityApi.createRestoreDrill({
        job_id: Number(selectedRestoreJob.id),
        backup_path: selectedRestoreJob.output_dir,
        backup_hash: selectedRestoreJob.package_hash,
        restore_target: restoreTarget.trim(),
        verification_notes: restoreNotes.trim(),
      });
      setRestoreDrills((prev) => [created, ...(prev || [])]);
      await refreshJobsAndDrills();
      setRestoreNotes('');
    } catch (e) {
      setError(e.message || '恢复演练记录失败');
    } finally {
      setCreatingRestoreDrill(false);
    }
  }, [refreshJobsAndDrills, restoreNotes, restoreTarget, selectedRestoreJob]);

  return {
    loading,
    running,
    error,
    settings,
    jobs,
    activeJob,
    savingRetention,
    restoreDrills,
    selectedRestoreJobId,
    restoreTarget,
    restoreNotes,
    creatingRestoreDrill,
    targetPreview,
    localBackupTargetPath,
    windowsBackupTargetPath,
    restoreEligibleJobs,
    setSettingField,
    setSelectedRestoreJobId,
    setRestoreTarget,
    setRestoreNotes,
    saveRetention,
    runNow,
    runFullBackupNow,
    handleSelectJob,
    submitRestoreDrill,
  };
}
