import React, { useEffect, useMemo, useRef, useState } from 'react';
import { dataSecurityApi } from '../features/dataSecurity/api';
import { cronToSchedule, scheduleToCron, formatSchedule } from '../features/dataSecurity/scheduleUtils';

const formatTime = (ms) => {
  if (!ms) return '';
  const d = new Date(ms);
  return d.toLocaleString();
};

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
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [settings, setSettings] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
  const pollTimer = useRef(null);

  // 定时备份状态
  const [incrementalSchedule, setIncrementalSchedule] = useState(
    cronToSchedule(null) || { type: 'daily', hour: '18', minute: '30' }
  );
  const [fullBackupSchedule, setFullBackupSchedule] = useState(
    cronToSchedule(null) || { type: 'weekly', hour: '04', minute: '00', weekday: '1' }
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

  const loadAll = async () => {
    setError(null);
    setLoading(true);
    try {
      const [s, j] = await Promise.all([dataSecurityApi.getSettings(), dataSecurityApi.listJobs(30)]);
      setSettings(s);
      // 更新定时备份状态
      setIncrementalSchedule(cronToSchedule(s.incremental_schedule) || { type: 'daily', hour: '18', minute: '30' });
      setFullBackupSchedule(cronToSchedule(s.full_backup_schedule) || { type: 'weekly', hour: '04', minute: '00', weekday: '1' });
      setJobs(j.jobs || []);
      const latest = (j.jobs || [])[0];
      setActiveJob(latest || null);
      setRunning(latest ? ['queued', 'running'].includes(latest.status) : false);
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
      const isRunning = ['queued', 'running'].includes(job.status);
      setRunning(isRunning);
      if (!isRunning) {
        const j = await dataSecurityApi.listJobs(30);
        setJobs(j.jobs || []);
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
      const settingsWithCron = {
        ...settings,
        incremental_schedule: scheduleToCron(incrementalSchedule),
        full_backup_schedule: scheduleToCron(fullBackupSchedule),
      };
      const updated = await dataSecurityApi.updateSettings(settingsWithCron);
      setSettings(updated);
    } catch (e) {
      setError(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const runNow = async () => {
    setError(null);
    try {
      if (!settings) return;
      if (settings.target_mode === 'local') {
        if (!String(settings.target_local_dir || '').trim()) {
          setError('请先填写"本机目标目录"，再点击"立即备份"。');
          return;
        }
      } else {
        if (!String(settings.target_ip || '').trim() || !String(settings.target_share_name || '').trim()) {
          setError('请先填写"目标电脑 IP"和"共享名"，再点击"立即备份"。');
          return;
        }
      }

      // "立即备份"默认使用你当前看到的设置（无需先点"保存设置"）
      setSaving(true);
      const updated = await dataSecurityApi.updateSettings(settings);
      setSettings(updated);
      setSaving(false);

      const res = await dataSecurityApi.runBackup();
      if (res.job_id) {
        setRunning(true);
        await pollActiveJob(res.job_id);
        if (pollTimer.current) clearInterval(pollTimer.current);
        pollTimer.current = setInterval(() => pollActiveJob(res.job_id), 1000);
      }
    } catch (e) {
      setError(e.message || '启动失败');
      setSaving(false);
    }
  };

  const runFullBackupNow = async () => {
    setError(null);
    try {
      if (!settings) return;
      if (settings.target_mode === 'local') {
        if (!String(settings.target_local_dir || '').trim()) {
          setError('请先填写"本机目标目录"，再点击"全量备份"。');
          return;
        }
      } else {
        if (!String(settings.target_ip || '').trim() || !String(settings.target_share_name || '').trim()) {
          setError('请先填写"目标电脑 IP"和"共享名"，再点击"全量备份"。');
          return;
        }
      }

      setSaving(true);
      const updated = await dataSecurityApi.updateSettings(settings);
      setSettings(updated);
      setSaving(false);

      const res = await dataSecurityApi.runFullBackup();
      if (res.job_id) {
        setRunning(true);
        await pollActiveJob(res.job_id);
        if (pollTimer.current) clearInterval(pollTimer.current);
        pollTimer.current = setInterval(() => pollActiveJob(res.job_id), 1000);
      }
    } catch (e) {
      setError(e.message || '全量备份启动失败');
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: '12px' }}>加载中…</div>;

  return (
    <div style={{ maxWidth: '980px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>数据安全</h2>
        <div style={{ display: 'flex', gap: '10px' }}>
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
            }}
          >
            {running ? '备份中…' : '立即备份'}
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
            }}
          >
            {running ? '备份中…' : '全量备份'}
          </button>
          <button
            onClick={saveSettings}
            disabled={saving || !settings}
            data-testid="ds-save"
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              cursor: saving ? 'not-allowed' : 'pointer',
              background: 'white',
            }}
          >
            {saving ? '保存中…' : '保存设置'}
          </button>
        </div>
      </div>

      {error && (
        <div data-testid="ds-error" style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
          {error}
        </div>
      )}

      <Card title="备份设置">
        <div style={{ display: 'grid', gap: '12px' }}>
          <label style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={!!settings?.enabled}
              onChange={(e) => setSettings((p) => ({ ...p, enabled: e.target.checked }))}
              data-testid="ds-enabled"
            />
            启用定时备份
          </label>

          <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '16px', marginTop: '8px' }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#1f2937' }}>⏰ 定时备份设置</h4>

            {/* 增量备份时间 */}
            <label style={{ display: 'block', marginBottom: '16px' }}>
              <div style={{ fontWeight: 600, marginBottom: '8px' }}>增量备份时间</div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span>每天</span>
                <input
                  type="time"
                  value={`${incrementalSchedule.hour}:${incrementalSchedule.minute}`}
                  onChange={(e) => {
                    const [hour, minute] = e.target.value.split(':');
                    setIncrementalSchedule({ type: 'daily', hour, minute });
                  }}
                  style={{ padding: '6px 8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
                />
              </div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: '4px' }}>
                预览：{formatSchedule(incrementalSchedule)} 执行增量备份
              </div>
            </label>

            {/* 全量备份时间 */}
            <label style={{ display: 'block', marginBottom: '12px' }}>
              <div style={{ fontWeight: 600, marginBottom: '8px' }}>全量备份时间</div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span>每周</span>
                <select
                  value={fullBackupSchedule.weekday}
                  onChange={(e) => {
                    setFullBackupSchedule({ ...fullBackupSchedule, weekday: e.target.value });
                  }}
                  style={{ padding: '6px 8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
                >
                  <option value="1">周一</option>
                  <option value="2">周二</option>
                  <option value="3">周三</option>
                  <option value="4">周四</option>
                  <option value="5">周五</option>
                  <option value="6">周六</option>
                  <option value="0">周日</option>
                </select>
                <input
                  type="time"
                  value={`${fullBackupSchedule.hour}:${fullBackupSchedule.minute}`}
                  onChange={(e) => {
                    const [hour, minute] = e.target.value.split(':');
                    setFullBackupSchedule({ ...fullBackupSchedule, hour, minute });
                  }}
                  style={{ padding: '6px 8px', border: '1px solid #d1d5db', borderRadius: '6px' }}
                />
              </div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: '4px' }}>
                预览：{formatSchedule(fullBackupSchedule)} 执行全量备份
              </div>
            </label>

            <div style={{ padding: '10px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '8px', color: '#166534', fontSize: '0.85rem' }}>
              💡 系统会按照设定的时间自动执行备份
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <label>
              目标类型
              <select
                value={settings?.target_mode || 'share'}
                onChange={(e) => setSettings((p) => ({ ...p, target_mode: e.target.value }))}
                data-testid="ds-target-mode"
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              >
                <option value="share">另一台电脑共享目录（推荐）</option>
                <option value="local">本机目录</option>
              </select>
            </label>

            <div style={{ color: '#6b7280', fontSize: '0.9rem', alignSelf: 'end' }}>
              说明：这里填写的是“后端服务器所在电脑”的路径/共享信息。
            </div>
          </div>

          {settings?.target_mode === 'local' ? (
            <label>
              本机目标目录（绝对路径）
              <input data-testid="ds-target-local-dir"
                value={settings?.target_local_dir || ''}
                onChange={(e) => setSettings((p) => ({ ...p, target_local_dir: e.target.value }))}
                placeholder="例如：D:\\backup\\ragflowauth"
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              />
            </label>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <label>
                目标电脑 IP
                <input
                  value={settings?.target_ip || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_ip: e.target.value }))}
                  data-testid="ds-target-ip"
                  placeholder="例如：192.168.1.10"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                共享名（Share Name）
                <input
                  value={settings?.target_share_name || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_share_name: e.target.value }))}
                  data-testid="ds-target-share-name"
                  placeholder="例如：backup"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                子目录（可空）
                <input
                  value={settings?.target_subdir || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_subdir: e.target.value }))}
                  data-testid="ds-target-subdir"
                  placeholder="例如：ragflowauth"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <div data-testid="ds-target-preview" style={{ gridColumn: '1 / -1', color: '#6b7280', fontSize: '0.9rem' }}>
                预览：{targetPreview || '（未完整填写）'}
              </div>
            </div>
          )}

          <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '12px' }} />

          <label>
            RAGFlow docker-compose.yml 路径（容器内路径）
            <input
              value={settings?.ragflow_compose_path || ''}
              onChange={(e) => setSettings((p) => ({ ...p, ragflow_compose_path: e.target.value }))}
              data-testid="ds-ragflow-compose-path"
              placeholder="/app/ragflow_compose/docker-compose.yml"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
            />
            <div style={{ color: '#6b7280', marginTop: '6px', fontSize: '0.9rem' }}>
              如果找不到该文件，备份会提示你。
            </div>
          </label>

          <label>
            <div style={{ color: '#6b7280', marginTop: '6px', fontSize: '0.9rem' }}>
              只需要填写 docker-compose.yml 路径即可。系统会自动识别 Compose 项目名（必要时会提示你怎么处理）。
            </div>
          </label>

          <label style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={!!settings?.ragflow_stop_services}
              onChange={(e) => setSettings((p) => ({ ...p, ragflow_stop_services: e.target.checked }))}
              data-testid="ds-ragflow-stop-services"
            />
            备份前停止 RAGFlow 服务（更一致，但会短暂停机）
          </label>

          <label style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={!!settings?.full_backup_include_images}
              onChange={(e) => setSettings((p) => ({ ...p, full_backup_include_images: e.target.checked }))}
              data-testid="ds-full-backup-include-images"
            />
            全量备份包含 Docker 镜像（体积较大，但可离线恢复）
          </label>

          <label>
            本项目数据库路径（默认 data/auth.db）
            <input
              value={settings?.auth_db_path || 'data/auth.db'}
              onChange={(e) => setSettings((p) => ({ ...p, auth_db_path: e.target.value }))}
              data-testid="ds-auth-db-path"
              placeholder="data/auth.db"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
            />
          </label>

          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            上次定时触发：{settings?.last_run_at_ms ? formatTime(settings.last_run_at_ms) : '暂无'}
          </div>
        </div>
      </Card>

      <Card title="备份进度">
        {activeJob ? (
          <>
            <div data-testid="ds-active-job" style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <div>
                <div data-testid="ds-active-job-status" style={{ fontWeight: 600 }}>
                  #{activeJob.id} {activeJob.status}
                </div>
                <div data-testid="ds-active-job-message" style={{ color: '#6b7280', fontSize: '0.9rem' }}>
                  {activeJob.message || ''} {activeJob.output_dir ? `（输出：${activeJob.output_dir}）` : ''}
                </div>
              </div>
              <div style={{ minWidth: '140px', textAlign: 'right', color: '#6b7280' }}>
                {activeJob.started_at_ms ? formatTime(activeJob.started_at_ms) : ''}
              </div>
            </div>
            <div style={{ marginTop: '10px' }}>
              <ProgressBar value={activeJob.progress} />
              <div data-testid="ds-active-job-progress" style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.9rem' }}>{activeJob.progress}%</div>
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
            {jobs.map((j) => (
              <div
                key={j.id}
                data-testid={`ds-job-row-${j.id}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '10px',
                  cursor: 'pointer',
                }}
                onClick={() => {
                  setActiveJob(j);
                  if (['queued', 'running'].includes(j.status)) {
                    setRunning(true);
                    if (pollTimer.current) clearInterval(pollTimer.current);
                    pollTimer.current = setInterval(() => pollActiveJob(j.id), 1000);
                  }
                }}
              >
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <div style={{ fontWeight: 700 }}>#{j.id}</div>
                  <div style={{ color: j.status === 'success' ? '#059669' : j.status === 'failed' ? '#dc2626' : '#6b7280' }}>
                    {j.status}
                  </div>
                  <div style={{ color: '#6b7280' }}>{j.message || ''}</div>
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>{formatTime(j.created_at_ms)}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default DataSecurity;
