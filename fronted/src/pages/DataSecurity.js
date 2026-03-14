import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { dataSecurityApi } from '../features/dataSecurity/api';
import { cronToSchedule, formatSchedule } from '../features/dataSecurity/scheduleUtils';

const formatTime = (ms) => {
  if (!ms) return '';
  const d = new Date(ms);
  return d.toLocaleString();
};

const BACKUP_STATUS_LABELS = {
  queued: '排队中',
  running: '执行中',
  success: '成功',
  failed: '失败',
  canceled: '已取消',
};

const formatBackupStatus = (status) => {
  const key = String(status || '').trim().toLowerCase();
  return BACKUP_STATUS_LABELS[key] || String(status || '-');
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
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [settings, setSettings] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
  const [savingRetention, setSavingRetention] = useState(false);
  const pollTimer = useRef(null);
  const showAdvanced = useMemo(
    () => new URLSearchParams(location.search).get('advanced') === '1',
    [location.search]
  );

  const saveRetention = async () => {
    if (!settings) return;
    setError(null);
    setSavingRetention(true);
    try {
      const n = Number(settings.backup_retention_max ?? 30);
      const clamped = Math.max(1, Math.min(100, Number.isFinite(n) ? n : 30));
      const s = await dataSecurityApi.updateSettings({ backup_retention_max: clamped });
      // Backward-compatible: older backends may not return `backup_retention_max` in the payload.
      // Keep the UI value stable to avoid "save -> reset to 30" confusion.
      setSettings((prev) => ({ ...(prev || {}), ...(s || {}), backup_retention_max: (s && s.backup_retention_max != null) ? s.backup_retention_max : clamped }));
    } catch (e) {
      setError(e.message || '保存失败');
    } finally {
      setSavingRetention(false);
    }
  };

  // 定时备份（目前 UI 隐藏设置区，但保留状态以便内部逻辑/后续扩展）
  const [incrementalSchedule, setIncrementalSchedule] = useState(
    cronToSchedule(null) || { type: 'daily', hour: '18', minute: '30' }
  );
  const [fullBackupSchedule, setFullBackupSchedule] = useState(
    cronToSchedule(null) || { type: 'weekly', hour: '04', minute: '00', weekday: '1' }
  );

  // 定时备份状态
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

  const runNow = async () => {
    setError(null);
    try {
      const res = await dataSecurityApi.runBackup();
      if (res.job_id) {
        setRunning(true);
        await pollActiveJob(res.job_id);
        if (pollTimer.current) clearInterval(pollTimer.current);
        pollTimer.current = setInterval(() => pollActiveJob(res.job_id), 1000);
      }
    } catch (e) {
      setError(e.message || '启动失败');
    }
  };

  const runFullBackupNow = async () => {
    setError(null);
    try {
      const res = await dataSecurityApi.runFullBackup();
      if (res.job_id) {
        setRunning(true);
        await pollActiveJob(res.job_id);
        if (pollTimer.current) clearInterval(pollTimer.current);
        pollTimer.current = setInterval(() => pollActiveJob(res.job_id), 1000);
      }
    } catch (e) {
      setError(e.message || '全量备份启动失败');
    }
  };

  if (loading) return <div style={{ padding: '12px' }}>加载中…</div>;

  return (
    <div style={{ maxWidth: '980px' }} data-testid="data-security-page">
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
        </div>
      </div>

      {error && (
        <div data-testid="ds-error" style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
          {error}
        </div>
      )}

      <Card title="备份保留策略">
        <div style={{ display: 'grid', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ color: '#6b7280' }}>
              备份路径： <span style={{ color: '#111827' }}>{settings?.backup_target_path || targetPreview || '-'}</span>
            </div>
            <div style={{ color: '#6b7280' }}>
              当前备份数量： <span style={{ color: '#111827', fontWeight: 700 }}>{Number(settings?.backup_pack_count || 0)}</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              保留最多备份至
              <input
                type="number"
                min={1}
                max={100}
                step={1}
                value={settings?.backup_retention_max ?? 30}
                onChange={(e) => {
                  const raw = Number(e.target.value);
                  const v = Math.max(1, Math.min(100, Number.isFinite(raw) ? raw : 30));
                  setSettings((p) => ({ ...(p || {}), backup_retention_max: v }));
                }}
                style={{ width: '90px', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px' }}
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
              }}
            >
              {savingRetention ? '保存中…' : '保存'}
            </button>

            <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
              超出数量，系统会在备份任务完成后自动删除最老的 `migration_pack_*`。
            </div>
          </div>
        </div>
      </Card>

      {showAdvanced && (
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
                placeholder="例如：备份目录/项目目录"
                style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
              />
            </label>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <label>
                目标电脑地址（IP）
                <input
                  value={settings?.target_ip || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_ip: e.target.value }))}
                  data-testid="ds-target-ip"
                  placeholder="例如：192.168.1.10"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                共享名
                <input
                  value={settings?.target_share_name || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_share_name: e.target.value }))}
                  data-testid="ds-target-share-name"
                  placeholder="例如：备份"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                子目录（可空）
                <input
                  value={settings?.target_subdir || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_subdir: e.target.value }))}
                  data-testid="ds-target-subdir"
                  placeholder="例如：项目备份"
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
            RAGFlow 编排文件路径（容器内路径）
            <input
              value={settings?.ragflow_compose_path || ''}
              onChange={(e) => setSettings((p) => ({ ...p, ragflow_compose_path: e.target.value }))}
              data-testid="ds-ragflow-compose-path"
              placeholder="例如：容器内编排文件路径"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
            />
            <div style={{ color: '#6b7280', marginTop: '6px', fontSize: '0.9rem' }}>
              如果找不到该文件，备份会提示你。
            </div>
          </label>

          <label>
            <div style={{ color: '#6b7280', marginTop: '6px', fontSize: '0.9rem' }}>
              只需要填写编排文件路径即可。系统会自动识别项目名（必要时会提示你怎么处理）。
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
            全量备份包含镜像文件（体积较大，但可离线恢复）
          </label>

          <label>
            本项目数据库路径（默认值见输入框）
            <input
              value={settings?.auth_db_path || 'data/auth.db'}
              onChange={(e) => setSettings((p) => ({ ...p, auth_db_path: e.target.value }))}
              data-testid="ds-auth-db-path"
              placeholder="例如：项目数据目录/认证库文件路径"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
            />
          </label>

          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            上次定时触发：{settings?.last_run_at_ms ? formatTime(settings.last_run_at_ms) : '暂无'}
          </div>
        </div>
      </Card>
      )}

      <Card title="备份进度">
        {activeJob ? (
          <>
            <div data-testid="ds-active-job" style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <div>
                <div data-testid="ds-active-job-status" style={{ fontWeight: 600 }}>
                  #{activeJob.id} {formatBackupStatus(activeJob.status)}
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
                    {formatBackupStatus(j.status)}
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
