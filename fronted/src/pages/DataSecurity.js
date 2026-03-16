import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { dataSecurityApi } from '../features/dataSecurity/api';
import { cronToSchedule, formatSchedule } from '../features/dataSecurity/scheduleUtils';
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

const listToLines = (value) =>
  Array.isArray(value)
    ? value
        .map((item) => String(item || '').trim())
        .filter(Boolean)
        .join('\n')
    : '';

const linesToList = (value) =>
  String(value || '')
    .split(/\r?\n|,/)
    .map((item) => String(item || '').trim())
    .filter(Boolean);

const buildEgressDraft = (config) => {
  const rules = config?.sensitivity_rules || {};
  return {
    mode: String(config?.mode || 'intranet'),
    sensitive_classification_enabled: Boolean(config?.sensitive_classification_enabled),
    auto_desensitize_enabled: Boolean(config?.auto_desensitize_enabled),
    high_sensitive_block_enabled: Boolean(config?.high_sensitive_block_enabled),
    sensitivity_rules_low: listToLines(rules?.low || []),
    sensitivity_rules_medium: listToLines(rules?.medium || []),
    sensitivity_rules_high: listToLines(rules?.high || []),
  };
};

const buildEgressPayload = (draft) => ({
  mode: String(draft?.mode || 'intranet'),
  sensitive_classification_enabled: Boolean(draft?.sensitive_classification_enabled),
  auto_desensitize_enabled: Boolean(draft?.auto_desensitize_enabled),
  high_sensitive_block_enabled: Boolean(draft?.high_sensitive_block_enabled),
  sensitivity_rules: {
    low: linesToList(draft?.sensitivity_rules_low),
    medium: linesToList(draft?.sensitivity_rules_medium),
    high: linesToList(draft?.sensitivity_rules_high),
  },
});

const ProgressBar = ({ value }) => {
  const pct = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div style={{ width: '100%', background: '#dbe7f3', borderRadius: '999px', height: 10, overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: 10, background: pct >= 100 ? '#1f8a57' : '#0d5ea6', transition: 'width 0.2s' }} />
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
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [settings, setSettings] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
  const [savingRetention, setSavingRetention] = useState(false);
  const [egressDraft, setEgressDraft] = useState(buildEgressDraft(null));
  const [savingEgress, setSavingEgress] = useState(false);
  const [egressMessage, setEgressMessage] = useState('');
  const pollTimer = useRef(null);

  const showAdvanced = useMemo(() => new URLSearchParams(location.search).get('advanced') === '1', [location.search]);

  const [incrementalSchedule, setIncrementalSchedule] = useState(
    cronToSchedule(null) || { type: 'daily', hour: '18', minute: '30' }
  );
  const [fullBackupSchedule, setFullBackupSchedule] = useState(
    cronToSchedule(null) || { type: 'weekly', hour: '04', minute: '00', weekday: '1' }
  );

  const saveRetention = async () => {
    if (!settings) return;
    setError(null);
    setSavingRetention(true);
    try {
      const n = Number(settings.backup_retention_max ?? 30);
      const clamped = Math.max(1, Math.min(100, Number.isFinite(n) ? n : 30));
      const s = await dataSecurityApi.updateSettings({ backup_retention_max: clamped });
      setSettings((prev) => ({
        ...(prev || {}),
        ...(s || {}),
        backup_retention_max: s && s.backup_retention_max != null ? s.backup_retention_max : clamped,
      }));
    } catch (e) {
      setError(normalizeDisplayError(e?.message ?? e, '保存失败'));
    } finally {
      setSavingRetention(false);
    }
  };

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
    setEgressMessage('');
    setLoading(true);
    try {
      const [s, j, egressConfig] = await Promise.all([
        dataSecurityApi.getSettings(),
        dataSecurityApi.listJobs(30),
        dataSecurityApi.getEgressConfig().catch(() => null),
      ]);
      setSettings(s);
      setEgressDraft(buildEgressDraft(egressConfig));
      setIncrementalSchedule(cronToSchedule(s.incremental_schedule) || { type: 'daily', hour: '18', minute: '30' });
      setFullBackupSchedule(cronToSchedule(s.full_backup_schedule) || { type: 'weekly', hour: '04', minute: '00', weekday: '1' });
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
      setError(normalizeDisplayError(e?.message ?? e, '启动失败'));
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
      setError(normalizeDisplayError(e?.message ?? e, '全量备份启动失败'));
    }
  };

  const saveEgressConfig = async () => {
    setError(null);
    setEgressMessage('');
    setSavingEgress(true);
    try {
      const payload = buildEgressPayload(egressDraft);
      const updated = await dataSecurityApi.updateEgressConfig(payload);
      setEgressDraft(buildEgressDraft(updated));
      setEgressMessage('对话安全策略已保存并生效');
    } catch (e) {
      const msg = normalizeDisplayError(e?.message ?? e, '保存对话安全策略失败');
      setError(msg);
      setEgressMessage(msg);
    } finally {
      setSavingEgress(false);
    }
  };

  if (loading) return <div className="medui-empty">加载中...</div>;

  return (
    <div className="admin-med-page" style={{ maxWidth: 980 }} data-testid="data-security-page">
      <div className="admin-med-head">
        <h2 className="admin-med-title">数据安全</h2>
        <div className="admin-med-actions">
          <button onClick={runNow} disabled={running} data-testid="ds-run-now" type="button" className="medui-btn medui-btn--primary">
            {running ? '备份中...' : '立即备份'}
          </button>
          <button onClick={runFullBackupNow} disabled={running} data-testid="ds-run-full" type="button" className="medui-btn medui-btn--secondary">
            {running ? '备份中...' : '全量备份'}
          </button>
        </div>
      </div>

      {error ? <div data-testid="ds-error" className="admin-med-danger">{error}</div> : null}

      <Card title="备份保留策略">
        <div className="admin-med-grid">
          <div className="admin-med-head" style={{ justifyContent: 'space-between' }}>
            <div className="admin-med-inline-note">
              备份路径：<span style={{ color: '#17324d' }}>{settings?.backup_target_path || targetPreview || '-'}</span>
            </div>
            <div className="admin-med-inline-note">
              当前备份数量：<span style={{ color: '#17324d', fontWeight: 700 }}>{Number(settings?.backup_pack_count || 0)}</span>
            </div>
          </div>

          <div className="admin-med-actions" style={{ alignItems: 'center' }}>
            <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
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
                className="medui-input"
                style={{ width: 90 }}
              />
              个（1~100）
            </label>

            <button onClick={saveRetention} disabled={savingRetention} data-testid="ds-retention-save" type="button" className="medui-btn medui-btn--primary">
              {savingRetention ? '保存中...' : '保存'}
            </button>

            <div className="admin-med-inline-note">
              超出数量时，系统将在备份完成后自动清理最早的迁移包。
            </div>
          </div>
        </div>
      </Card>

      <Card title="对话外发安全策略">
        <div className="admin-med-grid">
          <div className="admin-med-inline-note">这里配置“分级、脱敏、拦截”规则。聊天时会按此策略执行并进行可视化展示。</div>

          <div className="admin-med-grid admin-med-grid--2">
            <label>
              外发模式
              <select
                data-testid="ds-egress-mode"
                value={egressDraft.mode}
                onChange={(e) => setEgressDraft((prev) => ({ ...prev, mode: e.target.value }))}
                className="medui-select"
                style={{ marginTop: 6 }}
              >
                <option value="intranet">内网模式（仅内网出网）</option>
                <option value="extranet">外网模式（允许策略化外发）</option>
              </select>
            </label>
            <div className="admin-med-inline-note" style={{ alignSelf: 'end' }}>
              建议默认使用内网模式。若启用外网模式，请同时配置敏感规则。
            </div>
          </div>

          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              type="checkbox"
              data-testid="ds-egress-sensitive-enabled"
              checked={!!egressDraft.sensitive_classification_enabled}
              onChange={(e) => setEgressDraft((prev) => ({ ...prev, sensitive_classification_enabled: e.target.checked }))}
            />
            启用敏感分级（识别敏感词并计算敏感等级）
          </label>

          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              type="checkbox"
              data-testid="ds-egress-auto-desensitize"
              checked={!!egressDraft.auto_desensitize_enabled}
              onChange={(e) => setEgressDraft((prev) => ({ ...prev, auto_desensitize_enabled: e.target.checked }))}
            />
            启用自动脱敏（命中规则时自动替换敏感内容）
          </label>

          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              type="checkbox"
              data-testid="ds-egress-high-block"
              checked={!!egressDraft.high_sensitive_block_enabled}
              onChange={(e) => setEgressDraft((prev) => ({ ...prev, high_sensitive_block_enabled: e.target.checked }))}
            />
            启用高敏拦截（高敏内容直接拦截，不发送到模型）
          </label>

          <div className="admin-med-grid admin-med-grid--3">
            <label>
              低敏规则（每行一个）
              <textarea
                data-testid="ds-egress-rules-low"
                value={egressDraft.sensitivity_rules_low}
                onChange={(e) => setEgressDraft((prev) => ({ ...prev, sensitivity_rules_low: e.target.value }))}
                placeholder="例如：公开信息"
                rows={6}
                className="medui-textarea"
                style={{ marginTop: 6 }}
              />
            </label>

            <label>
              中敏规则（每行一个）
              <textarea
                data-testid="ds-egress-rules-medium"
                value={egressDraft.sensitivity_rules_medium}
                onChange={(e) => setEgressDraft((prev) => ({ ...prev, sensitivity_rules_medium: e.target.value }))}
                placeholder="例如：内部资料"
                rows={6}
                className="medui-textarea"
                style={{ marginTop: 6 }}
              />
            </label>

            <label>
              高敏规则（每行一个）
              <textarea
                data-testid="ds-egress-rules-high"
                value={egressDraft.sensitivity_rules_high}
                onChange={(e) => setEgressDraft((prev) => ({ ...prev, sensitivity_rules_high: e.target.value }))}
                placeholder="例如：身份证号"
                rows={6}
                className="medui-textarea"
                style={{ marginTop: 6 }}
              />
            </label>
          </div>

          <div className="admin-med-actions" style={{ alignItems: 'center' }}>
            <button data-testid="ds-egress-save" onClick={saveEgressConfig} disabled={savingEgress} type="button" className="medui-btn medui-btn--primary">
              {savingEgress ? '保存中...' : '保存对话安全策略'}
            </button>
            {egressMessage ? (
              <div data-testid="ds-egress-message" style={{ color: egressMessage.includes('失败') ? '#a53a3a' : '#176940' }}>
                {egressMessage}
              </div>
            ) : null}
          </div>
        </div>
      </Card>

      {showAdvanced ? (
        <Card title="备份设置（高级）">
          <div className="admin-med-grid">
            <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={!!settings?.enabled}
                onChange={(e) => setSettings((p) => ({ ...p, enabled: e.target.checked }))}
                data-testid="ds-enabled"
              />
              启用定时备份
            </label>

            <div style={{ borderTop: '1px solid #deebf8', paddingTop: 12 }}>
              <h4 style={{ margin: '0 0 12px 0', color: '#1f2937' }}>定时备份计划</h4>

              <label style={{ display: 'block', marginBottom: 16 }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>增量备份时间</div>
                <div className="admin-med-actions" style={{ alignItems: 'center' }}>
                  <span>每天</span>
                  <input
                    type="time"
                    value={`${incrementalSchedule.hour}:${incrementalSchedule.minute}`}
                    onChange={(e) => {
                      const [hour, minute] = e.target.value.split(':');
                      setIncrementalSchedule({ type: 'daily', hour, minute });
                    }}
                    className="medui-input"
                    style={{ width: 140 }}
                  />
                </div>
                <div className="admin-med-small" style={{ marginTop: 4 }}>预览：{formatSchedule(incrementalSchedule)} 执行增量备份</div>
              </label>

              <label style={{ display: 'block', marginBottom: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>全量备份时间</div>
                <div className="admin-med-actions" style={{ alignItems: 'center' }}>
                  <span>每周</span>
                  <select
                    value={fullBackupSchedule.weekday}
                    onChange={(e) => setFullBackupSchedule({ ...fullBackupSchedule, weekday: e.target.value })}
                    className="medui-select"
                    style={{ width: 120 }}
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
                    className="medui-input"
                    style={{ width: 140 }}
                  />
                </div>
                <div className="admin-med-small" style={{ marginTop: 4 }}>预览：{formatSchedule(fullBackupSchedule)} 执行全量备份</div>
              </label>

              <div className="admin-med-success">系统会按计划自动执行备份任务。</div>
            </div>

            <div className="admin-med-grid admin-med-grid--2">
              <label>
                目标类型
                <select
                  value={settings?.target_mode || 'share'}
                  onChange={(e) => setSettings((p) => ({ ...p, target_mode: e.target.value }))}
                  data-testid="ds-target-mode"
                  className="medui-select"
                  style={{ marginTop: 6 }}
                >
                  <option value="share">另一台电脑共享目录（推荐）</option>
                  <option value="local">本机目录</option>
                </select>
              </label>
              <div className="admin-med-inline-note" style={{ alignSelf: 'end' }}>
                此处填写的是后端服务所在机器可访问的路径或共享信息。
              </div>
            </div>

            {settings?.target_mode === 'local' ? (
              <label>
                本机目标目录（绝对路径）
                <input
                  data-testid="ds-target-local-dir"
                  value={settings?.target_local_dir || ''}
                  onChange={(e) => setSettings((p) => ({ ...p, target_local_dir: e.target.value }))}
                  placeholder="示例：数据备份目录"
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
                    data-testid="ds-target-ip"
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
                    data-testid="ds-target-share-name"
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
                    data-testid="ds-target-subdir"
                    placeholder="示例：项目备份目录"
                    className="medui-input"
                    style={{ marginTop: 6 }}
                  />
                </label>
                <div data-testid="ds-target-preview" className="admin-med-inline-note" style={{ gridColumn: '1 / -1' }}>
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
                data-testid="ds-ragflow-compose-path"
                placeholder="示例：容器内编排文件路径"
                className="medui-input"
                style={{ marginTop: 6 }}
              />
              <div className="admin-med-inline-note" style={{ marginTop: 6 }}>如果找不到该文件，备份会给出提示。</div>
            </label>

            <div className="admin-med-inline-note">这里只需填写编排文件路径，系统会自动识别项目信息。</div>

            <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={!!settings?.ragflow_stop_services}
                onChange={(e) => setSettings((p) => ({ ...p, ragflow_stop_services: e.target.checked }))}
                data-testid="ds-ragflow-stop-services"
              />
              备份前停止 RAGFlow 服务（数据更一致，但会短暂停机）
            </label>

            <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={!!settings?.full_backup_include_images}
                onChange={(e) => setSettings((p) => ({ ...p, full_backup_include_images: e.target.checked }))}
                data-testid="ds-full-backup-include-images"
              />
              全量备份包含镜像文件（体积更大，但可离线恢复）
            </label>

            <label>
              本项目数据库路径
              <input
                value={settings?.auth_db_path || ''}
                onChange={(e) => setSettings((p) => ({ ...p, auth_db_path: e.target.value }))}
                data-testid="ds-auth-db-path"
                placeholder="示例：项目数据目录中的认证库文件路径"
                className="medui-input"
                style={{ marginTop: 6 }}
              />
            </label>

            <div className="admin-med-inline-note">上次定时触发：{settings?.last_run_at_ms ? formatTime(settings.last_run_at_ms) : '暂无'}</div>
          </div>
        </Card>
      ) : null}

      <Card title="备份进度">
        {activeJob ? (
          <>
            <div data-testid="ds-active-job" className="admin-med-head" style={{ alignItems: 'center' }}>
              <div>
                <div data-testid="ds-active-job-status" style={{ fontWeight: 700 }}>
                  #{activeJob.id} {formatBackupStatus(activeJob.status)}
                </div>
                <div data-testid="ds-active-job-message" className="admin-med-inline-note">
                  {activeJob.message ? normalizeDisplayError(activeJob.message, '任务执行中') : ''} {activeJob.output_dir ? `（输出：${activeJob.output_dir}）` : ''}
                </div>
              </div>
              <div className="admin-med-inline-note" style={{ minWidth: 140, textAlign: 'right' }}>
                {activeJob.started_at_ms ? formatTime(activeJob.started_at_ms) : ''}
              </div>
            </div>
            <div style={{ marginTop: 10 }}>
              <ProgressBar value={activeJob.progress} />
              <div data-testid="ds-active-job-progress" className="admin-med-inline-note" style={{ marginTop: 6 }}>{activeJob.progress}%</div>
            </div>
            {activeJob.detail ? (
              <div data-testid="ds-active-job-detail" className="admin-med-danger" style={{ marginTop: 10 }}>
                {normalizeDisplayError(activeJob.detail, '请查看任务详情')}
              </div>
            ) : null}
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
                data-testid={`ds-job-row-${j.id}`}
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
