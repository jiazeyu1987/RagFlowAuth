import React, { useEffect, useMemo, useRef, useState } from 'react';
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

const DataSecurity = () => {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [settings, setSettings] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
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

  const localBackupTargetPath = useMemo(
    () => settings?.local_backup_target_path || settings?.backup_target_path || '/app/data/backups',
    [settings]
  );

  const windowsBackupTargetPath = useMemo(
    () => settings?.windows_backup_target_path || settings?.replica_target_path || targetPreview || '',
    [settings, targetPreview]
  );

  const loadAll = async () => {
    setError(null);
    setLoading(true);
    try {
      const [s, j] = await Promise.all([dataSecurityApi.getSettings(), dataSecurityApi.listJobs(30)]);
      const nextJobs = j?.jobs || [];
      const latest = nextJobs[0] || null;
      setSettings(s || {});
      setJobs(nextJobs);
      setActiveJob(latest);
      setRunning(latest ? isRunningStatus(latest.status) : false);
    } catch (e) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const pollActiveJob = async (jobId) => {
    try {
      const job = await dataSecurityApi.getJob(jobId);
      setActiveJob(job);
      const nextRunning = isRunningStatus(job?.status);
      setRunning(nextRunning);
      if (!nextRunning) {
        const j = await dataSecurityApi.listJobs(30);
        setJobs(j?.jobs || []);
        if (pollTimer.current) {
          clearInterval(pollTimer.current);
          pollTimer.current = null;
        }
      }
    } catch {
      // ignore
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

  const saveSettings = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await dataSecurityApi.updateSettings(settings);
      setSettings(updated);
    } catch (e) {
      setError(e.message || '保存失败');
    } finally {
      setSaving(false);
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
      if (!settings) return;
      if (settings.target_mode === 'local' && !String(settings.target_local_dir || '').trim()) {
        setError('请先填写 Windows 目标目录，再点击“立即备份”。');
        return;
      }
      if (settings.target_mode !== 'local' && (!String(settings.target_ip || '').trim() || !String(settings.target_share_name || '').trim())) {
        setError('请先填写目标电脑 IP 和共享名，再点击“立即备份”。');
        return;
      }

      setSaving(true);
      const updated = await dataSecurityApi.updateSettings(settings);
      setSettings(updated);
      setSaving(false);

      const res = await dataSecurityApi.runBackup();
      if (res?.job_id) await startPollingJob(res.job_id);
    } catch (e) {
      setError(e.message || '启动失败');
      setSaving(false);
    }
  };

  const runFullBackupNow = async () => {
    setError(null);
    try {
      if (!settings) return;
      if (settings.target_mode === 'local' && !String(settings.target_local_dir || '').trim()) {
        setError('请先填写 Windows 目标目录，再点击“全量备份”。');
        return;
      }
      if (settings.target_mode !== 'local' && (!String(settings.target_ip || '').trim() || !String(settings.target_share_name || '').trim())) {
        setError('请先填写目标电脑 IP 和共享名，再点击“全量备份”。');
        return;
      }

      setSaving(true);
      const updated = await dataSecurityApi.updateSettings(settings);
      setSettings(updated);
      setSaving(false);

      const res = await dataSecurityApi.runFullBackup();
      if (res?.job_id) await startPollingJob(res.job_id);
    } catch (e) {
      setError(e.message || '全量备份启动失败');
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: '12px' }}>加载中...</div>;

  return (
    <div style={{ maxWidth: '980px', width: '100%' }} data-testid="data-security-test-page">
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
          <button
            onClick={saveSettings}
            disabled={saving || !settings}
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              cursor: saving ? 'not-allowed' : 'pointer',
              background: 'white',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {saving ? '保存中...' : '保存设置'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
          {error}
        </div>
      )}

      <Card title="路径概览">
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '12px' }}>
          <div style={{ padding: '12px', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
            <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>本地正式备份</div>
            <div style={{ marginTop: '6px', color: '#111827', wordBreak: 'break-all' }}>{localBackupTargetPath || '-'}</div>
            <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
              数量: {Number(settings?.local_backup_pack_count ?? settings?.backup_pack_count ?? 0)}
            </div>
          </div>
          <div style={{ padding: '12px', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
            <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>Windows 备份</div>
            <div style={{ marginTop: '6px', color: '#111827', wordBreak: 'break-all' }}>{windowsBackupTargetPath || '未配置'}</div>
            <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
              数量: {Number(settings?.windows_backup_pack_count || 0)}
            </div>
          </div>
        </div>
      </Card>

      <Card title="Windows 备份设置">
        <div style={{ display: 'grid', gap: '12px' }}>
          <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
            <input
              type="checkbox"
              checked={!!settings?.enabled}
              onChange={(e) => setSettings((p) => ({ ...p, enabled: e.target.checked }))}
            />
            启用自动备份
          </label>

          <label>
            目标类型
            <select
              value={settings?.target_mode || 'share'}
              onChange={(e) => setSettings((p) => ({ ...p, target_mode: e.target.value }))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
            >
              <option value="share">共享目录</option>
              <option value="local">本机目录</option>
            </select>
          </label>

          {settings?.target_mode === 'local' ? (
            <label>
              Windows 目标目录
              <input
                value={settings?.target_local_dir || ''}
                onChange={(e) => setSettings((p) => ({ ...p, target_local_dir: e.target.value }))}
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              />
            </label>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: '12px' }}>
              <label>
                目标电脑 IP
                <input
                  value={settings?.target_ip || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_ip: e.target.value }))}
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                共享名
                <input
                  value={settings?.target_share_name || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_share_name: e.target.value }))}
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                子目录
                <input
                  value={settings?.target_subdir || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_subdir: e.target.value }))}
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
            </div>
          )}

          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            预览: {targetPreview || windowsBackupTargetPath || '未配置'}
          </div>
        </div>
      </Card>

      <Card title="备份进度">
        {activeJob ? (
          <>
            <div
              style={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                justifyContent: 'space-between',
                gap: '10px',
                alignItems: isMobile ? 'stretch' : 'center',
              }}
            >
              <div style={{ display: 'grid', gap: '4px' }}>
                <div style={{ fontWeight: 600 }}>
                  #{activeJob.id} {activeJob.status}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>{activeJob.message || ''}</div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  本地: {activeJob.output_dir ? `成功 | ${activeJob.output_dir}` : '未生成'}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  Windows: {String(activeJob.replication_status || 'skipped')} {activeJob.replica_path ? `| ${activeJob.replica_path}` : ''}
                </div>
              </div>
              <div style={{ minWidth: isMobile ? 'auto' : '140px', textAlign: isMobile ? 'left' : 'right', color: '#6b7280' }}>
                {activeJob.started_at_ms ? formatTime(activeJob.started_at_ms) : ''}
              </div>
            </div>
            <div style={{ marginTop: '10px' }}>
              <ProgressBar value={activeJob.progress} />
              <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.9rem' }}>{activeJob.progress}%</div>
            </div>
            {activeJob.detail ? (
              <div style={{ marginTop: '10px', padding: '10px', background: '#fef2f2', color: '#991b1b', borderRadius: '8px' }}>
                {activeJob.detail}
              </div>
            ) : null}
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
            {jobs.map((j) => (
              <div
                key={j.id}
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
                  setActiveJob(j);
                  if (isRunningStatus(j.status)) {
                    setRunning(true);
                    if (pollTimer.current) clearInterval(pollTimer.current);
                    pollTimer.current = setInterval(() => pollActiveJob(j.id), 1000);
                  }
                }}
              >
                <div style={{ display: 'grid', gap: '4px' }}>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ fontWeight: 700 }}>#{j.id}</div>
                    <div style={{ color: '#6b7280' }}>{j.status}</div>
                    <div style={{ color: '#6b7280' }}>{j.message || ''}</div>
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    本地: {j.output_dir ? '成功' : '未生成'} | Windows: {String(j.replication_status || 'skipped')}
                  </div>
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem', textAlign: isMobile ? 'left' : 'right' }}>{formatTime(j.created_at_ms)}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default DataSecurity;
