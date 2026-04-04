import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { dataSecurityApi } from '../features/dataSecurity/api';

const MOBILE_BREAKPOINT = 768;

const formatTime = (ms) => {
  if (!ms) return '';
  const d = new Date(Number(ms));
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString();
};

const isRunningStatus = (status) => ['queued', 'running', 'canceling'].includes(String(status || '').toLowerCase());

const ProgressBar = ({ value }) => {
  const pct = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div style={{ width: '100%', background: '#e5e7eb', borderRadius: '999px', height: '10px', overflow: 'hidden' }}>
      <div
        style={{
          width: `${pct}%`,
          height: '10px',
          background: pct >= 100 ? '#10b981' : '#3b82f6',
          transition: 'width 0.2s',
        }}
      />
    </div>
  );
};

const Card = ({ title, children }) => (
  <div style={{ marginTop: '16px', background: 'white', borderRadius: '12px', padding: '16px', border: '1px solid #e5e7eb' }}>
    <h3 style={{ marginTop: 0 }}>{title}</h3>
    {children}
  </div>
);

const statusColor = (status) => {
  const text = String(status || '').toLowerCase();
  if (text === 'failed') return '#dc2626';
  if (text === 'completed' || text === 'success' || text === 'succeeded') return '#059669';
  if (isRunningStatus(text) || text === 'pending') return '#2563eb';
  return '#374151';
};

const localBackupLabel = (job) => {
  if (job?.output_dir) return '成功';
  if (String(job?.status || '').toLowerCase() === 'failed') return '失败';
  return '未生成';
};

const windowsBackupLabel = (job) => {
  const status = String(job?.replication_status || '').toLowerCase();
  if (status === 'succeeded') return '成功';
  if (status === 'failed') return '失败';
  if (status === 'skipped') return '未执行';
  if (status === 'pending') return '进行中';
  return '未执行';
};

const DataSecurity = () => {
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
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

  const showAdvanced = useMemo(
    () => new URLSearchParams(location.search).get('advanced') === '1',
    [location.search]
  );

  const targetPreview = useMemo(() => {
    if (!settings) return '';
    if (settings.target_mode === 'local') return settings.target_local_dir || '';
    const ip = (settings.target_ip || '').trim();
    const share = (settings.target_share_name || '').trim().replace(/^\\\\+|\\\\+$/g, '').replace(/^\/+|\/+$/g, '');
    const sub = (settings.target_subdir || '').trim().replace(/^\\\\+|\\\\+$/g, '').replace(/^\/+|\/+$/g, '');
    if (!ip || !share) return '';
    return sub ? `\\\\${ip}\\${share}\\${sub}` : `\\\\${ip}\\${share}`;
  }, [settings]);

  const localBackupTargetPath = useMemo(
    () => settings?.local_backup_target_path || settings?.backup_target_path || '/app/data/backups',
    [settings]
  );

  const windowsBackupTargetPath = useMemo(
    () => settings?.windows_backup_target_path || settings?.replica_target_path || targetPreview || '',
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

  const pickRestoreJobId = (nextJobs, prevValue = '') => {
    const eligible = (nextJobs || []).filter((job) => !!String(job?.output_dir || '').trim());
    if (prevValue && eligible.some((job) => String(job.id) === String(prevValue))) {
      return String(prevValue);
    }
    return eligible[0] ? String(eligible[0].id) : '';
  };

  const loadAll = async () => {
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
  };

  const refreshJobsAndDrills = async () => {
    const [jobsResp, drillsResp] = await Promise.all([
      dataSecurityApi.listJobs(30),
      dataSecurityApi.listRestoreDrills(30),
    ]);
    const nextJobs = Array.isArray(jobsResp?.jobs) ? jobsResp.jobs : [];
    const nextDrills = Array.isArray(drillsResp?.items) ? drillsResp.items : [];
    setJobs(nextJobs);
    setRestoreDrills(nextDrills);
    setSelectedRestoreJobId((prev) => pickRestoreJobId(nextJobs, prev));
  };

  const pollActiveJob = async (jobId) => {
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
    } catch {
      // Keep polling resilient to transient API failures.
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    loadAll();
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, []);

  const saveRetention = async () => {
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
  };

  const startPollingJob = async (jobId) => {
    setRunning(true);
    await pollActiveJob(jobId);
    if (pollTimer.current) clearInterval(pollTimer.current);
    pollTimer.current = setInterval(() => pollActiveJob(jobId), 1000);
  };

  const runNow = async () => {
    setError(null);
    try {
      const res = await dataSecurityApi.runBackup();
      if (res?.job_id) await startPollingJob(res.job_id);
    } catch (e) {
      setError(e.message || '启动失败');
    }
  };

  const runFullBackupNow = async () => {
    setError(null);
    try {
      const res = await dataSecurityApi.runFullBackup();
      if (res?.job_id) await startPollingJob(res.job_id);
    } catch (e) {
      setError(e.message || '全量备份启动失败');
    }
  };

  const submitRestoreDrill = async () => {
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
  };

  if (loading) return <div style={{ padding: '12px' }}>加载中...</div>;

  return (
    <div style={{ maxWidth: '980px', width: '100%' }} data-testid="data-security-page">
      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          gap: '12px',
          alignItems: isMobile ? 'stretch' : 'center',
        }}
      >
        <h2 style={{ margin: 0 }}>数据安全</h2>
        <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '10px', width: isMobile ? '100%' : 'auto' }}>
          <button
            onClick={runNow}
            disabled={running}
            data-testid="ds-run-now"
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              cursor: running ? 'not-allowed' : 'pointer',
              background: running ? '#9ca3af' : '#3b82f6',
              color: 'white',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {running ? '备份中...' : '立即备份'}
          </button>
          <button
            onClick={runFullBackupNow}
            disabled={running}
            data-testid="ds-run-full"
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              cursor: running ? 'not-allowed' : 'pointer',
              background: running ? '#9ca3af' : '#8b5cf6',
              color: 'white',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {running ? '备份中...' : '全量备份'}
          </button>
        </div>
      </div>

      {error && (
        <div data-testid="ds-error" style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
          {error}
        </div>
      )}

      <Card title="备份保留策略">
        <div style={{ display: 'grid', gap: '12px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '12px' }}>
            <div style={{ padding: '12px', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
              <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>本地备份路径</div>
              <div style={{ marginTop: '6px', color: '#111827', wordBreak: 'break-all' }}>{localBackupTargetPath || '-'}</div>
              <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
                备份数量: <span style={{ color: '#111827', fontWeight: 700 }}>{Number(settings?.local_backup_pack_count ?? settings?.backup_pack_count ?? 0)}</span>
              </div>
            </div>
            <div style={{ padding: '12px', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
              <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>Windows 备份路径</div>
              <div style={{ marginTop: '6px', color: '#111827', wordBreak: 'break-all' }}>{windowsBackupTargetPath || '未配置'}</div>
              <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
                备份数量:{' '}
                <span style={{ color: '#111827', fontWeight: 700 }}>{Number(settings?.windows_backup_pack_count || 0)}</span>
                {settings?.windows_backup_pack_count_skipped ? '（统计已跳过）' : ''}
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              flexDirection: isMobile ? 'column' : 'row',
              gap: '10px',
              alignItems: isMobile ? 'stretch' : 'center',
            }}
          >
            <label
              style={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                gap: '10px',
                alignItems: isMobile ? 'stretch' : 'center',
              }}
            >
              保留最多备份至
              <input
                type="number"
                min={1}
                max={100}
                step={1}
                value={settings?.backup_retention_max ?? 30}
                onChange={(e) => {
                  const raw = Number(e.target.value);
                  const next = Math.max(1, Math.min(100, Number.isFinite(raw) ? raw : 30));
                  setSettings((prev) => ({ ...(prev || {}), backup_retention_max: next }));
                }}
                style={{ width: isMobile ? '100%' : '90px', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', boxSizing: 'border-box' }}
              />
              个（1~100）
            </label>

            <button
              onClick={saveRetention}
              disabled={savingRetention}
              data-testid="ds-retention-save"
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: 'none',
                cursor: savingRetention ? 'not-allowed' : 'pointer',
                background: savingRetention ? '#9ca3af' : '#111827',
                color: 'white',
                width: isMobile ? '100%' : 'auto',
              }}
            >
              {savingRetention ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </Card>

      {showAdvanced && (
        <Card title="Windows 备份设置">
          <div style={{ display: 'grid', gap: '12px' }}>
            <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '10px', color: '#475569', fontSize: '0.9rem' }}>
              本地正式备份目录固定为 <strong>{localBackupTargetPath}</strong>。
              Windows 备份使用下方配置解析目标路径，优先使用服务器挂载路径，其次使用手动填写的共享或本地路径。
            </div>

            <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <input
                type="checkbox"
                checked={!!settings?.enabled}
                onChange={(e) => setSettings((prev) => ({ ...(prev || {}), enabled: e.target.checked }))}
                data-testid="ds-enabled"
              />
              启用定时备份
            </label>

            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '12px' }}>
              <label>
                目标类型
                <select
                  value={settings?.target_mode || 'share'}
                  onChange={(e) => setSettings((prev) => ({ ...(prev || {}), target_mode: e.target.value }))}
                  data-testid="ds-target-mode"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                >
                  <option value="share">共享目录</option>
                  <option value="local">本机目录</option>
                </select>
              </label>

              <div style={{ color: '#6b7280', fontSize: '0.9rem', alignSelf: 'end' }}>
                当前 Windows 目标预览: <span style={{ color: '#111827' }}>{windowsBackupTargetPath || '未配置'}</span>
              </div>
            </div>

            {(settings?.target_mode || 'share') === 'local' ? (
              <label>
                Windows 目标目录（绝对路径）
                <input
                  data-testid="ds-target-local-dir"
                  value={settings?.target_local_dir || ''}
                  onChange={(e) => setSettings((prev) => ({ ...(prev || {}), target_local_dir: e.target.value }))}
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: '12px' }}>
                <label>
                  目标电脑 IP
                  <input
                    value={settings?.target_ip || ''}
                    onChange={(e) => setSettings((prev) => ({ ...(prev || {}), target_ip: e.target.value }))}
                    data-testid="ds-target-ip"
                    style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                  />
                </label>
                <label>
                  共享名
                  <input
                    value={settings?.target_share_name || ''}
                    onChange={(e) => setSettings((prev) => ({ ...(prev || {}), target_share_name: e.target.value }))}
                    data-testid="ds-target-share-name"
                    style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                  />
                </label>
                <label>
                  子目录（可空）
                  <input
                    value={settings?.target_subdir || ''}
                    onChange={(e) => setSettings((prev) => ({ ...(prev || {}), target_subdir: e.target.value }))}
                    data-testid="ds-target-subdir"
                    style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                  />
                </label>
                <div data-testid="ds-target-preview" style={{ gridColumn: isMobile ? 'auto' : '1 / -1', color: '#6b7280', fontSize: '0.9rem' }}>
                  预览: {targetPreview || '（未完整填写）'}
                </div>
              </div>
            )}

            <label>
              RAGFlow docker-compose.yml 路径
              <input
                value={settings?.ragflow_compose_path || ''}
                onChange={(e) => setSettings((prev) => ({ ...(prev || {}), ragflow_compose_path: e.target.value }))}
                data-testid="ds-ragflow-compose-path"
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              />
            </label>

            <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <input
                type="checkbox"
                checked={!!settings?.ragflow_stop_services}
                onChange={(e) => setSettings((prev) => ({ ...(prev || {}), ragflow_stop_services: e.target.checked }))}
                data-testid="ds-ragflow-stop-services"
              />
              备份前停止 RAGFlow 服务
            </label>

            <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <input
                type="checkbox"
                checked={!!settings?.full_backup_include_images}
                onChange={(e) => setSettings((prev) => ({ ...(prev || {}), full_backup_include_images: e.target.checked }))}
                data-testid="ds-full-backup-include-images"
              />
              全量备份包含 Docker 镜像
            </label>

            <label>
              项目数据库路径
              <input
                value={settings?.auth_db_path || 'data/auth.db'}
                onChange={(e) => setSettings((prev) => ({ ...(prev || {}), auth_db_path: e.target.value }))}
                data-testid="ds-auth-db-path"
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              />
            </label>
          </div>
        </Card>
      )}

      <Card title="备份进度">
        {activeJob ? (
          <>
            <div
              data-testid="ds-active-job"
              style={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                justifyContent: 'space-between',
                gap: '10px',
                alignItems: isMobile ? 'stretch' : 'center',
              }}
            >
              <div style={{ display: 'grid', gap: '6px' }}>
                <div data-testid="ds-active-job-status" style={{ fontWeight: 600, color: statusColor(activeJob.status) }}>
                  #{activeJob.id} {activeJob.status}
                </div>
                <div data-testid="ds-active-job-message" style={{ color: '#6b7280', fontSize: '0.9rem' }}>
                  {activeJob.message || ''}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  本地备份: {localBackupLabel(activeJob)} {activeJob.output_dir ? `| ${activeJob.output_dir}` : ''}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  Windows 备份: {windowsBackupLabel(activeJob)} {activeJob.replica_path ? `| ${activeJob.replica_path}` : ''}
                </div>
                {activeJob.replication_error ? (
                  <div style={{ color: '#92400e', fontSize: '0.85rem' }}>Windows 说明: {activeJob.replication_error}</div>
                ) : null}
              </div>
              <div style={{ minWidth: isMobile ? 'auto' : '140px', textAlign: isMobile ? 'left' : 'right', color: '#6b7280' }}>
                {activeJob.started_at_ms ? formatTime(activeJob.started_at_ms) : ''}
              </div>
            </div>
            <div style={{ marginTop: '10px' }}>
              <ProgressBar value={activeJob.progress} />
              <div data-testid="ds-active-job-progress" style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.9rem' }}>
                {activeJob.progress}%
              </div>
            </div>
            {activeJob.detail && (
              <div data-testid="ds-active-job-detail" style={{ marginTop: '10px', padding: '10px', background: '#fef2f2', color: '#991b1b', borderRadius: '8px' }}>
                {activeJob.detail}
              </div>
            )}
          </>
        ) : (
          <div style={{ color: '#6b7280' }}>暂无备份记录</div>
        )}
      </Card>

      <Card title="备份记录">
        {jobs.length === 0 ? (
          <div style={{ color: '#6b7280' }}>暂无</div>
        ) : (
          <div style={{ display: 'grid', gap: '10px' }}>
            {jobs.map((job) => (
              <div
                key={job.id}
                data-testid={`ds-job-row-${job.id}`}
                style={{
                  display: 'flex',
                  flexDirection: isMobile ? 'column' : 'row',
                  justifyContent: 'space-between',
                  alignItems: isMobile ? 'stretch' : 'center',
                  padding: '10px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '10px',
                  cursor: 'pointer',
                }}
                onClick={() => {
                  setActiveJob(job);
                  if (job.output_dir) {
                    setSelectedRestoreJobId(String(job.id));
                  }
                  if (isRunningStatus(job.status)) {
                    setRunning(true);
                    if (pollTimer.current) clearInterval(pollTimer.current);
                    pollTimer.current = setInterval(() => pollActiveJob(job.id), 1000);
                  }
                }}
              >
                <div style={{ display: 'grid', gap: '4px' }}>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ fontWeight: 700 }}>#{job.id}</div>
                    <div style={{ color: statusColor(job.status) }}>{job.status}</div>
                    <div style={{ color: '#6b7280' }}>{job.message || ''}</div>
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    Hash: {job.package_hash || '未生成'}
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    本地备份: {localBackupLabel(job)} {job.output_dir ? `| ${job.output_dir}` : ''}
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    Windows 备份: {windowsBackupLabel(job)} {job.replica_path ? `| ${job.replica_path}` : ''}
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    验证: {job.verified_at_ms ? `${job.verified_by || '-'} @ ${formatTime(job.verified_at_ms)}` : '未验证'}
                  </div>
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem', textAlign: isMobile ? 'left' : 'right' }}>
                  {formatTime(job.created_at_ms)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="恢复演练">
        <div style={{ display: 'grid', gap: '10px' }}>
          <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '10px', color: '#475569', fontSize: '0.9rem' }}>
            恢复演练仅从本地备份执行数据恢复，Windows 备份不会用于演练恢复。
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '10px' }}>
            <label>
              本地备份任务
              <select
                data-testid="ds-restore-job-select"
                value={selectedRestoreJobId}
                onChange={(e) => setSelectedRestoreJobId(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              >
                <option value="">请选择</option>
                {restoreEligibleJobs.map((job) => (
                  <option key={job.id} value={String(job.id)}>
                    #{job.id} {job.kind || '-'} {job.status || '-'}
                  </option>
                ))}
              </select>
            </label>

            <label>
              恢复目标
              <input
                data-testid="ds-restore-target"
                value={restoreTarget}
                onChange={(e) => setRestoreTarget(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              />
            </label>

            <label>
              验证备注
              <input
                data-testid="ds-restore-notes"
                value={restoreNotes}
                onChange={(e) => setRestoreNotes(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              />
            </label>
          </div>

          {restoreEligibleJobs.length === 0 ? (
            <div style={{ color: '#6b7280' }}>当前没有可用于本地恢复演练的备份任务。</div>
          ) : null}

          <button
            type="button"
            onClick={submitRestoreDrill}
            data-testid="ds-restore-submit"
            disabled={creatingRestoreDrill}
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              cursor: creatingRestoreDrill ? 'not-allowed' : 'pointer',
              background: creatingRestoreDrill ? '#9ca3af' : '#111827',
              color: 'white',
              width: isMobile ? '100%' : 'fit-content',
            }}
          >
            {creatingRestoreDrill ? '记录中...' : '记录恢复演练'}
          </button>

          {restoreDrills.length === 0 ? (
            <div style={{ color: '#6b7280' }}>暂无恢复演练记录</div>
          ) : (
            <div style={{ display: 'grid', gap: '10px' }}>
              {restoreDrills.map((item) => (
                <div
                  key={item.drill_id}
                  data-testid={`ds-restore-row-${item.drill_id}`}
                  style={{ padding: '10px 12px', border: '1px solid #e5e7eb', borderRadius: '10px', display: 'grid', gap: '4px' }}
                >
                  <div style={{ fontWeight: 600 }}>
                    {item.drill_id} / job #{item.job_id} / {item.result}
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
                    target: {item.restore_target} | by: {item.executed_by} | at: {formatTime(item.executed_at_ms)}
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    path: {item.backup_path} | hash: {item.backup_hash}
                  </div>
                  <div style={{ color: '#374151', fontSize: '0.85rem' }}>
                    package validation: {item.package_validation_status || '-'} | acceptance: {item.acceptance_status || '-'}
                  </div>
                  <div style={{ color: '#374151', fontSize: '0.85rem' }}>
                    hash match: {String(!!item.hash_match)} | compare match: {String(!!item.compare_match)}
                  </div>
                  {item.actual_backup_hash ? (
                    <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                      actual hash: {item.actual_backup_hash}
                    </div>
                  ) : null}
                  {item.restored_auth_db_path ? (
                    <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                      restored auth.db: {item.restored_auth_db_path}
                    </div>
                  ) : null}
                  {item.verification_notes ? (
                    <div style={{ color: '#374151', fontSize: '0.9rem' }}>
                      notes: {item.verification_notes}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default DataSecurity;
