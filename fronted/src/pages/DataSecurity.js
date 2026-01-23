import React, { useEffect, useMemo, useRef, useState } from 'react';
import { dataSecurityApi } from '../features/dataSecurity/api';

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
      const updated = await dataSecurityApi.updateSettings(settings);
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
          setError('请先填写“本机目标目录”，再点击“立即备份”。');
          return;
        }
      } else {
        if (!String(settings.target_ip || '').trim() || !String(settings.target_share_name || '').trim()) {
          setError('请先填写“目标电脑 IP”和“共享名”，再点击“立即备份”。');
          return;
        }
      }

      // “立即备份”默认使用你当前看到的设置（无需先点“保存设置”）
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

  if (loading) return <div style={{ padding: '12px' }}>加载中…</div>;

  return (
    <div style={{ maxWidth: '980px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>数据安全</h2>
        <div style={{ display: 'flex', gap: '10px' }}>
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
            }}
          >
            {running ? '备份中…' : '立即备份'}
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
            }}
          >
            {saving ? '保存中…' : '保存设置'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
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
            />
            启用定时备份
          </label>

          <label>
            备份间隔（分钟）
            <input
              type="number"
              min="1"
              value={Number(settings?.interval_minutes || 1440)}
              onChange={(e) => setSettings((p) => ({ ...p, interval_minutes: Number(e.target.value || 1) }))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
            />
            <div style={{ color: '#6b7280', marginTop: '6px', fontSize: '0.9rem' }}>
              例如：1440 表示每天一次。启用后，系统会按间隔自动触发备份。
            </div>
          </label>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <label>
              目标类型
              <select
                value={settings?.target_mode || 'share'}
                onChange={(e) => setSettings((p) => ({ ...p, target_mode: e.target.value }))}
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
              <input
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
                  placeholder="例如：192.168.1.10"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                共享名（Share Name）
                <input
                  value={settings?.target_share_name || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_share_name: e.target.value }))}
                  placeholder="例如：backup"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <label>
                子目录（可空）
                <input
                  value={settings?.target_subdir || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_subdir: e.target.value }))}
                  placeholder="例如：ragflowauth"
                  style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px', marginTop: '6px' }}
                />
              </label>
              <div style={{ gridColumn: '1 / -1', color: '#6b7280', fontSize: '0.9rem' }}>
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
            />
            备份前停止 RAGFlow 服务（更一致，但会短暂停机）
          </label>

          <label>
            本项目数据库路径（默认 data/auth.db）
            <input
              value={settings?.auth_db_path || 'data/auth.db'}
              onChange={(e) => setSettings((p) => ({ ...p, auth_db_path: e.target.value }))}
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
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600 }}>
                  #{activeJob.id} {activeJob.status}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
                  {activeJob.message || ''} {activeJob.output_dir ? `（输出：${activeJob.output_dir}）` : ''}
                </div>
              </div>
              <div style={{ minWidth: '140px', textAlign: 'right', color: '#6b7280' }}>
                {activeJob.started_at_ms ? formatTime(activeJob.started_at_ms) : ''}
              </div>
            </div>
            <div style={{ marginTop: '10px' }}>
              <ProgressBar value={activeJob.progress} />
              <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.9rem' }}>{activeJob.progress}%</div>
            </div>
            {activeJob.detail && (
              <div style={{ marginTop: '10px', padding: '10px', background: '#fef2f2', color: '#991b1b', borderRadius: '8px' }}>
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
