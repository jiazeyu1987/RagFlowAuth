import React, { useEffect, useMemo, useRef, useState } from 'react';
import { dataSecurityApi } from '../features/dataSecurity/api';
import { normalizeDisplayError } from '../shared/utils/displayError';

const formatTime = (ms) => {
  if (!ms) return '';
  const d = new Date(ms);
  return d.toLocaleString('zh-CN');
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
    <div style={{ width: '100%', background: '#dbe7f3', borderRadius: '999px', height: 10, overflow: 'hidden' }}>
      <div
        style={{
          width: `${pct}%`,
          height: 10,
          background: pct >= 100 ? '#1f8a57' : '#0d5ea6',
          transition: 'width 0.2s',
        }}
      />
    </div>
  );
};

const Card = ({ title, children }) => (
  <section className="medui-surface medui-card-pad">
    <h3 style={{ marginTop: 0, marginBottom: 12, color: '#184469' }}>{title}</h3>
    {children}
  </section>
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
    const share = (settings.target_share_name || '').trim().replace(/^\\+|\\+$/g, '').replace(/^\/+|\/+$/g, '');
    const sub = (settings.target_subdir || '').trim().replace(/^\\+|\\+$/g, '').replace(/^\/+|\/+$/g, '');
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
      setError(normalizeDisplayError(e?.message ?? e, '加载失败'));
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
      setError(normalizeDisplayError(e?.message ?? e, '保存失败'));
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
      } else if (!String(settings.target_ip || '').trim() || !String(settings.target_share_name || '').trim()) {
        setError('请先填写“目标电脑地址”和“共享名”，再点击“立即备份”。');
        return;
      }

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
      setError(normalizeDisplayError(e?.message ?? e, '启动失败'));
      setSaving(false);
    }
  };

  const runFullBackupNow = async () => {
    setError(null);
    try {
      if (!settings) return;
      if (settings.target_mode === 'local') {
        if (!String(settings.target_local_dir || '').trim()) {
          setError('请先填写“本机目标目录”，再点击“全量备份”。');
          return;
        }
      } else if (!String(settings.target_ip || '').trim() || !String(settings.target_share_name || '').trim()) {
        setError('请先填写“目标电脑地址”和“共享名”，再点击“全量备份”。');
        return;
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
      setError(normalizeDisplayError(e?.message ?? e, '全量备份启动失败'));
      setSaving(false);
    }
  };

  if (loading) return <div className="medui-empty">加载中...</div>;

  return (
    <div className="admin-med-page" style={{ maxWidth: 980 }} data-testid="data-security-test-page">
      <div className="admin-med-head">
        <h2 className="admin-med-title">数据安全（测试）</h2>
        <div className="admin-med-actions">
          <button onClick={runNow} disabled={running} type="button" className="medui-btn medui-btn--primary">
            {running ? '备份中...' : '立即备份'}
          </button>
          <button onClick={runFullBackupNow} disabled={running} type="button" className="medui-btn medui-btn--secondary">
            {running ? '备份中...' : '全量备份'}
          </button>
          <button onClick={saveSettings} disabled={saving || !settings} type="button" className="medui-btn medui-btn--neutral">
            {saving ? '保存中...' : '保存设置'}
          </button>
        </div>
      </div>

      {error ? <div className="admin-med-danger">{error}</div> : null}

      <Card title="备份设置">
        <div className="admin-med-grid">
          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={!!settings?.enabled}
              onChange={(e) => setSettings((p) => ({ ...p, enabled: e.target.checked }))}
            />
            启用自动备份
          </label>

          <div style={{ borderTop: '1px solid #deebf8', paddingTop: 12 }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#1f2937' }}>定时备份设置</h4>
            <div className="admin-med-inline-note" style={{ marginBottom: 12 }}>
              使用五段式定时表达式配置时间，格式：分 时 日 月 周
            </div>

            <label>
              <div style={{ fontWeight: 700 }}>增量备份时间（默认：每天凌晨 2 点）</div>
              <input
                value={settings?.incremental_schedule || '0 2 * * *'}
                onChange={(e) => setSettings((p) => ({ ...p, incremental_schedule: e.target.value }))}
                placeholder="0 2 * * *"
                className="medui-input"
                style={{ marginTop: 6, fontFamily: 'Consolas, Menlo, monospace' }}
              />
              <div className="admin-med-small" style={{ marginTop: 4 }}>
                常用示例：`0 2 * * *`（每天 2 点） | `0 */6 * * *`（每 6 小时） | `30 1 * * *`（每天 1:30）
              </div>
            </label>

            <label style={{ marginTop: 12, display: 'block' }}>
              <div style={{ fontWeight: 700 }}>全量备份时间（默认：每周一凌晨 4 点）</div>
              <input
                value={settings?.full_backup_schedule || '0 4 * * 1'}
                onChange={(e) => setSettings((p) => ({ ...p, full_backup_schedule: e.target.value }))}
                placeholder="0 4 * * 1"
                className="medui-input"
                style={{ marginTop: 6, fontFamily: 'Consolas, Menlo, monospace' }}
              />
              <div className="admin-med-small" style={{ marginTop: 4 }}>
                常用示例：`0 4 * * 1`（周一 4 点） | `0 3 * * 0`（周日 3 点） | `0 2 1 * *`（每月 1 日 2 点）
              </div>
            </label>

            <div className="admin-med-success" style={{ marginTop: 12 }}>
              系统会按计划自动执行备份，备份完成后自动清理旧副本。
            </div>
          </div>

          <div style={{ borderTop: '1px solid #deebf8', paddingTop: 12 }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#1f2937' }}>备份目标设置</h4>
            <label>
              目标类型
              <select
                value={settings?.target_mode || 'share'}
                onChange={(e) => setSettings((p) => ({ ...p, target_mode: e.target.value }))}
                className="medui-select"
                style={{ marginTop: 6 }}
              >
                <option value="share">另一台电脑共享目录（推荐）</option>
                <option value="local">本机目录</option>
              </select>
            </label>
            <div className="admin-med-inline-note" style={{ marginTop: 8 }}>
              说明：这里填写的是后端服务所在机器可访问的路径或共享信息。
            </div>
          </div>

          {settings?.target_mode === 'local' ? (
            <label>
              本机目标目录（绝对路径）
              <input
                value={settings?.target_local_dir || ''}
                onChange={(e) => setSettings((p) => ({ ...p, target_local_dir: e.target.value }))}
                placeholder="示例：数据备份目录\\项目目录"
                className="medui-input"
                style={{ marginTop: 6 }}
              />
            </label>
          ) : (
            <div className="admin-med-grid admin-med-grid--3">
              <label>
                目标电脑地址（内网地址）
                <input
                  value={settings?.target_ip || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_ip: e.target.value }))}
                  placeholder="示例：内网地址"
                  className="medui-input"
                  style={{ marginTop: 6 }}
                />
              </label>
              <label>
                共享名
                <input
                  value={settings?.target_share_name || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_share_name: e.target.value }))}
                  placeholder="示例：备份共享目录"
                  className="medui-input"
                  style={{ marginTop: 6 }}
                />
              </label>
              <label>
                子目录（可空）
                <input
                  value={settings?.target_subdir || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_subdir: e.target.value }))}
                  placeholder="示例：项目备份目录"
                  className="medui-input"
                  style={{ marginTop: 6 }}
                />
              </label>
              <div className="admin-med-inline-note" style={{ gridColumn: '1 / -1' }}>
                预览：{targetPreview || '（未完整填写）'}
              </div>
            </div>
          )}

          <div style={{ borderTop: '1px solid #deebf8', paddingTop: 12 }} />

          <label>
            RAGFlow 编排文件路径（容器内路径）
            <input
              value={settings?.ragflow_compose_path || ''}
              onChange={(e) => setSettings((p) => ({ ...p, ragflow_compose_path: e.target.value }))}
              placeholder="示例：容器内编排文件路径"
              className="medui-input"
              style={{ marginTop: 6 }}
            />
            <div className="admin-med-inline-note" style={{ marginTop: 6 }}>
              如果找不到该文件，备份流程会给出提示。
            </div>
          </label>

          <div className="admin-med-inline-note">
            仅需填写编排文件路径，系统会自动识别项目信息并在必要时提示处理方式。
          </div>

          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={!!settings?.ragflow_stop_services}
              onChange={(e) => setSettings((p) => ({ ...p, ragflow_stop_services: e.target.checked }))}
            />
            备份前停止 RAGFlow 服务（数据更一致，但会短暂停机）
          </label>

          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={!!settings?.full_backup_include_images}
              onChange={(e) => setSettings((p) => ({ ...p, full_backup_include_images: e.target.checked }))}
            />
            全量备份包含镜像文件（体积较大，但可离线恢复）
          </label>

          <label>
            本项目数据库路径（默认值见输入框）
            <input
              value={settings?.auth_db_path || ''}
              onChange={(e) => setSettings((p) => ({ ...p, auth_db_path: e.target.value }))}
              placeholder="示例：项目数据目录\\认证库文件路径"
              className="medui-input"
              style={{ marginTop: 6 }}
            />
          </label>

          <div className="admin-med-inline-note">上次自动备份：{settings?.last_run_at_ms ? formatTime(settings.last_run_at_ms) : '暂无'}</div>
        </div>
      </Card>

      <Card title="备份进度">
        {activeJob ? (
          <>
            <div className="admin-med-head" style={{ alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700 }}>
                  #{activeJob.id} {formatBackupStatus(activeJob.status)}
                </div>
                <div className="admin-med-inline-note">
                  {activeJob.message ? normalizeDisplayError(activeJob.message, '任务执行中') : ''} {activeJob.output_dir ? `（输出：${activeJob.output_dir}）` : ''}
                </div>
              </div>
              <div className="admin-med-inline-note" style={{ minWidth: 140, textAlign: 'right' }}>
                {activeJob.started_at_ms ? formatTime(activeJob.started_at_ms) : ''}
              </div>
            </div>
            <div style={{ marginTop: 10 }}>
              <ProgressBar value={activeJob.progress} />
              <div className="admin-med-inline-note" style={{ marginTop: 6 }}>{activeJob.progress}%</div>
            </div>
            {activeJob.detail ? <div className="admin-med-danger" style={{ marginTop: 10 }}>{normalizeDisplayError(activeJob.detail, '请查看任务详情')}</div> : null}
          </>
        ) : (
          <div className="admin-med-inline-note">暂无备份记录</div>
        )}
      </Card>

      <Card title="备份记录">
        {jobs.length === 0 ? (
          <div className="admin-med-inline-note">暂无</div>
        ) : (
          <div className="admin-med-grid">
            {jobs.map((j) => (
              <div
                key={j.id}
                className="medui-surface"
                style={{ padding: '10px 12px', cursor: 'pointer' }}
                onClick={() => {
                  setActiveJob(j);
                  if (['queued', 'running'].includes(j.status)) {
                    setRunning(true);
                    if (pollTimer.current) clearInterval(pollTimer.current);
                    pollTimer.current = setInterval(() => pollActiveJob(j.id), 1000);
                  }
                }}
              >
                <div className="admin-med-head">
                  <div className="admin-med-actions" style={{ alignItems: 'center' }}>
                    <div style={{ fontWeight: 700 }}>#{j.id}</div>
                    <div style={{ color: j.status === 'success' ? '#176940' : j.status === 'failed' ? '#a53a3a' : '#60788e' }}>
                      {formatBackupStatus(j.status)}
                    </div>
                    <div className="admin-med-inline-note">{j.message ? normalizeDisplayError(j.message, '任务执行中') : ''}</div>
                  </div>
                  <div className="admin-med-small">{formatTime(j.created_at_ms)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default DataSecurity;
