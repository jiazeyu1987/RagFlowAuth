
import React, { useEffect, useState } from 'react';
import { notificationApi } from '../features/notification/api';

const CHANNEL_TYPES = ['email', 'dingtalk', 'in_app'];
const LABELS = {
  email: '邮件',
  dingtalk: '钉钉',
  in_app: '站内信',
  queued: '待发送',
  sent: '已发送',
  failed: '失败',
};
const STATUS_LABELS = {
  queued: LABELS.queued,
  sent: LABELS.sent,
  failed: LABELS.failed,
};
const DEFAULTS = {
  email: { channelId: 'email-main', name: '邮件通知', enabled: false },
  dingtalk: { channelId: 'dingtalk-main', name: '钉钉工作通知', enabled: false },
  in_app: { channelId: 'inapp-main', name: '站内信', enabled: true },
};
const DINGTALK_DEFAULT_RECIPIENT_MAP = {
  '025247281136343306': '025247281136343306',
  '3245020131886184': '3245020131886184',
  '204548010024278804': '204548010024278804',
};
const DINGTALK_FORM_DEFAULTS = {
  app_key: 'dingidnt7v7zbm5tqzyn',
  app_secret: 'gi-v0YEkV_SCwXo9vGvYgBJzEbQ4wS4WUXDwA7ZkqMuNflFu0JfdFW1TeJIxcOjC',
  agent_id: '4432005762',
  recipient_map_text: JSON.stringify(DINGTALK_DEFAULT_RECIPIENT_MAP, null, 2),
  api_base: 'https://api.dingtalk.com',
  oapi_base: 'https://oapi.dingtalk.com',
  timeout_seconds: '30',
};
const card = { background: '#fff', border: '1px solid #e5e7eb', borderRadius: 16, padding: 18 };
const input = { width: '100%', padding: '9px 10px', border: '1px solid #d1d5db', borderRadius: 10, boxSizing: 'border-box' };
const btn = { border: '1px solid #d1d5db', borderRadius: 10, background: '#fff', color: '#111827', cursor: 'pointer', padding: '8px 14px' };
const primaryBtn = { ...btn, background: '#2563eb', border: '1px solid #2563eb', color: '#fff' };
const table = { width: '100%', borderCollapse: 'collapse' };
const cell = { borderBottom: '1px solid #e5e7eb', padding: '10px 8px', textAlign: 'left', verticalAlign: 'top', fontSize: '0.92rem' };
const muted = { color: '#6b7280', fontSize: '0.9rem' };

const formatTime = (value) => {
  const ms = Number(value || 0);
  return Number.isFinite(ms) && ms > 0 ? new Date(ms).toLocaleString() : '-';
};

const toInt = (value, label) => {
  const text = String(value || '').trim();
  if (!text) return undefined;
  const parsed = Number(text);
  if (!Number.isInteger(parsed)) throw new Error(`${label} 必须是整数`);
  return parsed;
};

const clean = (value) => Object.fromEntries(Object.entries(value || {}).filter(([, item]) => item !== '' && item !== undefined && item !== null));
const flattenRules = (groups) => (groups || []).flatMap((group) => (group.items || []).map((item) => ({ ...item, group_key: group.group_key })));
const warningText = (item) => {
  const missing = (item.enabled_channel_types || []).filter((channelType) => !(item.has_enabled_channel_config_by_type || {})[channelType]);
  return missing.length ? `已勾选但未配置启用渠道：${missing.map((channelType) => LABELS[channelType] || channelType).join('、')}` : '';
};

const buildBuckets = (items) => {
  const buckets = { email: [], dingtalk: [], in_app: [] };
  (items || []).forEach((item) => {
    const channelType = String(item?.channel_type || '').trim().toLowerCase();
    if (buckets[channelType]) buckets[channelType].push(item);
  });
  return buckets;
};

const isDefaultDingtalkForm = (value) => {
  const form = value || {};
  return String(form.app_key || '').trim() === DINGTALK_FORM_DEFAULTS.app_key
    && String(form.app_secret || '') === DINGTALK_FORM_DEFAULTS.app_secret
    && String(form.agent_id || '').trim() === DINGTALK_FORM_DEFAULTS.agent_id
    && String(form.recipient_map_text || '').trim() === DINGTALK_FORM_DEFAULTS.recipient_map_text
    && String(form.api_base || '').trim() === DINGTALK_FORM_DEFAULTS.api_base
    && String(form.oapi_base || '').trim() === DINGTALK_FORM_DEFAULTS.oapi_base
    && String(form.timeout_seconds || '').trim() === DINGTALK_FORM_DEFAULTS.timeout_seconds;
};

const emptyForms = () => ({
  email: { ...DEFAULTS.email, host: '', port: '', username: '', password: '', use_tls: true, from_email: '', updated_at_ms: null },
  dingtalk: { ...DEFAULTS.dingtalk, ...DINGTALK_FORM_DEFAULTS, updated_at_ms: null },
  in_app: { ...DEFAULTS.in_app, updated_at_ms: null },
});

const buildForms = (items) => {
  const forms = emptyForms();
  const buckets = buildBuckets(items);
  const email = buckets.email[0];
  const ding = buckets.dingtalk[0];
  const inApp = buckets.in_app[0];
  if (email) {
    const config = email.config || {};
    forms.email = {
      channelId: email.channel_id || DEFAULTS.email.channelId,
      name: email.name || DEFAULTS.email.name,
      enabled: !!email.enabled,
      host: String(config.host || ''),
      port: config.port === undefined || config.port === null ? '' : String(config.port),
      username: String(config.username || ''),
      password: String(config.password || ''),
      use_tls: config.use_tls === undefined ? true : !!config.use_tls,
      from_email: String(config.from_email || ''),
      updated_at_ms: email.updated_at_ms || null,
    };
  }
  if (ding) {
    const config = ding.config || {};
    const recipientMap = config.recipient_map && !Array.isArray(config.recipient_map) && typeof config.recipient_map === 'object' && Object.keys(config.recipient_map).length > 0
      ? config.recipient_map
      : DINGTALK_DEFAULT_RECIPIENT_MAP;
    forms.dingtalk = {
      channelId: ding.channel_id || DEFAULTS.dingtalk.channelId,
      name: ding.name || DEFAULTS.dingtalk.name,
      enabled: !!ding.enabled,
      app_key: String(config.app_key || DINGTALK_FORM_DEFAULTS.app_key),
      app_secret: String(config.app_secret || DINGTALK_FORM_DEFAULTS.app_secret),
      agent_id: config.agent_id === undefined || config.agent_id === null || config.agent_id === '' ? DINGTALK_FORM_DEFAULTS.agent_id : String(config.agent_id),
      recipient_map_text: JSON.stringify(recipientMap, null, 2),
      api_base: String(config.api_base || DINGTALK_FORM_DEFAULTS.api_base),
      oapi_base: String(config.oapi_base || DINGTALK_FORM_DEFAULTS.oapi_base),
      timeout_seconds: config.timeout_seconds === undefined || config.timeout_seconds === null || config.timeout_seconds === '' ? DINGTALK_FORM_DEFAULTS.timeout_seconds : String(config.timeout_seconds),
      updated_at_ms: ding.updated_at_ms || null,
    };
  }
  if (inApp) forms.in_app = { channelId: inApp.channel_id || DEFAULTS.in_app.channelId, name: inApp.name || DEFAULTS.in_app.name, enabled: !!inApp.enabled, updated_at_ms: inApp.updated_at_ms || null };
  return forms;
};

export default function NotificationSettings() {
  const [activeTab, setActiveTab] = useState('rules');
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [channelsSaving, setChannelsSaving] = useState(false);
  const [rulesSaving, setRulesSaving] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [channels, setChannels] = useState([]);
  const [forms, setForms] = useState(emptyForms());
  const [rulesGroups, setRulesGroups] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [logsByJob, setLogsByJob] = useState({});
  const [expandedLogs, setExpandedLogs] = useState({});
  const [historyFilters, setHistoryFilters] = useState({ eventType: '', channelType: '', status: '' });

  const channelBuckets = buildBuckets(channels);
  const ruleItems = flattenRules(rulesGroups);
  const eventLabelByType = Object.fromEntries(ruleItems.map((item) => [item.event_type, item.event_label]));

  const loadHistory = async (filters = historyFilters) => {
    setHistoryLoading(true);
    try {
      const response = await notificationApi.listJobs({ limit: 100, eventType: filters.eventType, channelType: filters.channelType, status: filters.status });
      setJobs(Array.isArray(response?.items) ? response.items : []);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadPage = async ({ keepNotice = false } = {}) => {
    if (!keepNotice) setNotice('');
    setError('');
    setLoading(true);
    try {
      const [channelResponse, rulesResponse] = await Promise.all([notificationApi.listChannels(false), notificationApi.listRules()]);
      const nextChannels = Array.isArray(channelResponse?.items) ? channelResponse.items : [];
      setChannels(nextChannels);
      setForms(buildForms(nextChannels));
      setRulesGroups(Array.isArray(rulesResponse?.groups) ? rulesResponse.groups : []);
      await loadHistory(historyFilters);
    } catch (requestError) {
      setError(requestError?.message || '加载通知设置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadPage(); }, []);

  const setFormValue = (channelType, field, value) => setForms((prev) => ({ ...prev, [channelType]: { ...prev[channelType], [field]: value } }));
  const saveChannels = async () => {
    setError('');
    setNotice('');
    const requests = [];
    try {
      const email = forms.email;
      if (channelBuckets.email.length > 0 || email.enabled || ['host', 'port', 'username', 'password', 'from_email'].some((field) => String(email[field] || '').trim())) {
        requests.push({
          channelId: email.channelId,
          payload: {
            channel_type: 'email',
            name: email.name,
            enabled: !!email.enabled,
            config: clean({ host: String(email.host || '').trim(), port: toInt(email.port, '邮件端口'), username: String(email.username || '').trim(), password: String(email.password || ''), use_tls: !!email.use_tls, from_email: String(email.from_email || '').trim() }),
          },
        });
      }
      const ding = forms.dingtalk;
      if (channelBuckets.dingtalk.length > 0 || ding.enabled || !isDefaultDingtalkForm(ding)) {
        let recipientMap = {};
        try { recipientMap = JSON.parse(String(ding.recipient_map_text || '{}')); } catch { throw new Error('钉钉 recipient_map 必须是合法 JSON'); }
        if (recipientMap === null || Array.isArray(recipientMap) || typeof recipientMap !== 'object') throw new Error('钉钉 recipient_map 必须是对象');
        requests.push({
          channelId: ding.channelId,
          payload: {
            channel_type: 'dingtalk',
            name: ding.name,
            enabled: !!ding.enabled,
            config: clean({ app_key: String(ding.app_key || '').trim(), app_secret: String(ding.app_secret || ''), agent_id: String(ding.agent_id || '').trim(), recipient_map: recipientMap, api_base: String(ding.api_base || '').trim(), oapi_base: String(ding.oapi_base || '').trim(), timeout_seconds: toInt(ding.timeout_seconds, '钉钉超时时间') }),
          },
        });
      }
      requests.push({ channelId: forms.in_app.channelId, payload: { channel_type: 'in_app', name: forms.in_app.name, enabled: !!forms.in_app.enabled, config: {} } });
    } catch (requestError) {
      setError(requestError?.message || '基础渠道配置校验失败');
      return;
    }
    setChannelsSaving(true);
    try {
      for (const item of requests) await notificationApi.upsertChannel(item.channelId, item.payload);
      setNotice('基础渠道配置已保存');
      await loadPage({ keepNotice: true });
    } catch (requestError) {
      setError(requestError?.message || '保存基础渠道配置失败');
    } finally {
      setChannelsSaving(false);
    }
  };

  const toggleRule = (eventType, channelType) => setRulesGroups((prev) => prev.map((group) => ({
    ...group,
    items: (group.items || []).map((item) => {
      if (item.event_type !== eventType) return item;
      const exists = (item.enabled_channel_types || []).includes(channelType);
      const next = exists ? item.enabled_channel_types.filter((value) => value !== channelType) : [...(item.enabled_channel_types || []), channelType];
      return { ...item, enabled_channel_types: CHANNEL_TYPES.filter((value) => next.includes(value)) };
    }),
  })));

  const saveRules = async () => {
    setError('');
    setNotice('');
    setRulesSaving(true);
    try {
      const response = await notificationApi.upsertRules({ items: flattenRules(rulesGroups).map((item) => ({ event_type: item.event_type, enabled_channel_types: item.enabled_channel_types || [] })) });
      setRulesGroups(Array.isArray(response?.groups) ? response.groups : []);
      setNotice('通知规则已保存');
    } catch (requestError) {
      setError(requestError?.message || '保存通知规则失败');
    } finally {
      setRulesSaving(false);
    }
  };

  const applyHistory = async (filters = historyFilters) => {
    setError('');
    try { await loadHistory(filters); } catch (requestError) { setError(requestError?.message || '加载发送历史失败'); }
  };

  const toggleLogs = async (jobId) => {
    const key = String(jobId);
    if (expandedLogs[key]) { setExpandedLogs((prev) => ({ ...prev, [key]: false })); return; }
    try {
      if (!logsByJob[key]) {
        const response = await notificationApi.listJobLogs(jobId, 20);
        setLogsByJob((prev) => ({ ...prev, [key]: Array.isArray(response?.items) ? response.items : [] }));
      }
      setExpandedLogs((prev) => ({ ...prev, [key]: true }));
    } catch (requestError) {
      setError(requestError?.message || '加载任务日志失败');
    }
  };

  const runJobAction = async (action, successText) => {
    setError('');
    setNotice('');
    try {
      await action();
      setNotice(successText);
      await loadHistory(historyFilters);
    } catch (requestError) {
      setError(requestError?.message || '通知任务操作失败');
    }
  };

  const dispatchPending = async () => {
    setDispatching(true);
    await runJobAction(() => notificationApi.dispatchPending(100), '待发送任务已触发分发');
    setDispatching(false);
  };

  if (loading) return <div style={{ padding: 12 }}>正在加载通知设置...</div>;

  const renderChannelCard = (channelType) => {
    const form = forms[channelType];
    const duplicates = channelBuckets[channelType] || [];
    return (
      <div key={channelType} style={{ border: '1px solid #e5e7eb', borderRadius: 14, padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 700 }}>{LABELS[channelType]}</div>
            <div style={{ ...muted, marginTop: 4 }}>
              {channelType === 'in_app' ? '系统内置消息中心渠道。' : channelType === 'email' ? '用于 SMTP 邮件通知。' : '用于钉钉企业应用工作通知。'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}><input type="checkbox" checked={!!form.enabled} onChange={(event) => setFormValue(channelType, 'enabled', event.target.checked)} /><span>启用</span></label>
            <span style={muted}>渠道 ID：{form.channelId}</span>
            <span style={muted}>最近更新：{formatTime(form.updated_at_ms)}</span>
          </div>
        </div>
        {duplicates.length > 1 ? <div style={{ marginTop: 10, color: '#92400e', fontSize: '0.88rem' }}>当前存在 {duplicates.length} 个{LABELS[channelType]}渠道，本页只编辑最近更新的一个：{form.channelId}</div> : null}
        {channelType === 'email' ? <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 14 }}><label style={{ display: 'grid', gap: 6 }}><span>SMTP 主机</span><input data-testid="notification-email-host" style={input} value={form.host} onChange={(event) => setFormValue('email', 'host', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>端口</span><input data-testid="notification-email-port" style={input} value={form.port} onChange={(event) => setFormValue('email', 'port', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>用户名</span><input data-testid="notification-email-username" style={input} value={form.username} onChange={(event) => setFormValue('email', 'username', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>密码</span><input data-testid="notification-email-password" type="password" style={input} value={form.password} onChange={(event) => setFormValue('email', 'password', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>发件人邮箱</span><input data-testid="notification-email-from-email" style={input} value={form.from_email} onChange={(event) => setFormValue('email', 'from_email', event.target.value)} /></label><label style={{ display: 'inline-flex', gap: 8, alignItems: 'center', marginTop: 28 }}><input data-testid="notification-email-use-tls" type="checkbox" checked={!!form.use_tls} onChange={(event) => setFormValue('email', 'use_tls', event.target.checked)} /><span>启用 TLS</span></label></div> : null}
        {channelType === 'dingtalk' ? <div style={{ display: 'grid', gap: 12, marginTop: 14 }}><div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}><label style={{ display: 'grid', gap: 6 }}><span>App Key</span><input data-testid="notification-dingtalk-app-key" style={input} value={form.app_key} onChange={(event) => setFormValue('dingtalk', 'app_key', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>App Secret</span><input data-testid="notification-dingtalk-app-secret" type="password" style={input} value={form.app_secret} onChange={(event) => setFormValue('dingtalk', 'app_secret', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>Agent ID</span><input data-testid="notification-dingtalk-agent-id" style={input} value={form.agent_id} onChange={(event) => setFormValue('dingtalk', 'agent_id', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>API Base</span><input style={input} value={form.api_base} placeholder="https://api.dingtalk.com" onChange={(event) => setFormValue('dingtalk', 'api_base', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>OAPI Base</span><input style={input} value={form.oapi_base} placeholder="https://oapi.dingtalk.com" onChange={(event) => setFormValue('dingtalk', 'oapi_base', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>超时时间（秒）</span><input style={input} value={form.timeout_seconds} onChange={(event) => setFormValue('dingtalk', 'timeout_seconds', event.target.value)} /></label></div><label style={{ display: 'grid', gap: 6 }}><span>recipient_map（JSON）</span><textarea data-testid="notification-dingtalk-recipient-map" style={{ ...input, minHeight: 120, fontFamily: 'monospace', resize: 'vertical' }} value={form.recipient_map_text} onChange={(event) => setFormValue('dingtalk', 'recipient_map_text', event.target.value)} /></label></div> : null}
        {channelType === 'in_app' ? <div style={{ ...muted, marginTop: 14 }}>站内信渠道配置固定为 <code>{'{}'}</code>。</div> : null}
      </div>
    );
  };
  return (
    <div style={{ maxWidth: 1280, display: 'grid', gap: 16 }} data-testid="notification-settings-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0 }}>通知设置</h2>
          <div style={{ ...muted, marginTop: 6 }}>先配置渠道参数，再按业务事件勾选邮件、钉钉、站内信。</div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" data-testid="notification-tab-rules" style={activeTab === 'rules' ? primaryBtn : btn} onClick={() => setActiveTab('rules')}>通知规则</button>
          <button type="button" data-testid="notification-tab-history" style={activeTab === 'history' ? primaryBtn : btn} onClick={() => setActiveTab('history')}>发送历史</button>
          <button type="button" data-testid="notification-tab-channels" style={activeTab === 'channels' ? primaryBtn : btn} onClick={() => setActiveTab('channels')}>基础渠道配置</button>
        </div>
      </div>
      {error ? <div data-testid="notification-error" style={{ ...card, borderColor: '#fecaca', background: '#fef2f2', color: '#b91c1c' }}>{error}</div> : null}
      {notice ? <div style={{ ...card, borderColor: '#bbf7d0', background: '#f0fdf4', color: '#166534' }}>{notice}</div> : null}

      {activeTab === 'rules' ? (
        <div style={card}>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              saveRules();
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0 }}>通知规则</h3>
                <div style={{ ...muted, marginTop: 6 }}>每个事件可以单选、多选，也可以全部不选。</div>
              </div>
              <button type="submit" data-testid="notification-save-rules" style={primaryBtn} disabled={rulesSaving}>{rulesSaving ? '保存中...' : '保存通知规则'}</button>
            </div>
            <div style={{ display: 'grid', gap: 16, marginTop: 16 }}>
              {(rulesGroups || []).map((group) => (
                <div key={group.group_key} style={{ border: '1px solid #e5e7eb', borderRadius: 14, overflow: 'hidden' }}>
                  <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', background: '#f9fafb', fontWeight: 700 }}>{group.group_label}</div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={table}>
                      <thead><tr><th style={cell}>事件</th><th style={cell}>邮件</th><th style={cell}>钉钉</th><th style={cell}>站内信</th><th style={cell}>风险提示</th></tr></thead>
                      <tbody>
                        {(group.items || []).map((item) => (
                          <tr key={item.event_type}>
                            <td style={cell}><div style={{ fontWeight: 600 }}>{item.event_label}</div><div style={muted}>{item.event_type}</div></td>
                            {CHANNEL_TYPES.map((channelType) => <td key={`${item.event_type}-${channelType}`} style={cell}><label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}><input type="checkbox" data-testid={`notification-rule-${item.event_type}-${channelType}`} checked={(item.enabled_channel_types || []).includes(channelType)} onChange={() => toggleRule(item.event_type, channelType)} /><span>{LABELS[channelType]}</span></label></td>)}
                            <td style={cell}>{warningText(item) ? <span style={{ color: '#92400e' }}>{warningText(item)}</span> : <span style={{ color: '#047857' }}>已配置</span>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </form>
        </div>
      ) : activeTab === 'channels' ? (
        <div style={card}>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              saveChannels();
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0 }}>基础渠道配置</h3>
                <div style={{ ...muted, marginTop: 6 }}>钉钉 recipient_map 的 value 必须是钉钉 userId。</div>
              </div>
              <button type="submit" data-testid="notification-save-channels" style={primaryBtn} disabled={channelsSaving}>{channelsSaving ? '保存中...' : '保存基础渠道配置'}</button>
            </div>
            <div style={{ display: 'grid', gap: 14, marginTop: 16 }}>{CHANNEL_TYPES.map(renderChannelCard)}</div>
          </form>
        </div>
      ) : (
        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0 }}>发送历史</h3>
              <div style={{ ...muted, marginTop: 6 }}>查看通知任务、投递日志，并支持重试、重发与手动分发。</div>
            </div>
            <button type="button" data-testid="notification-dispatch-pending" style={btn} onClick={dispatchPending} disabled={dispatching}>{dispatching ? '分发中...' : '分发待处理任务'}</button>
          </div>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 16 }}>
            <label style={{ display: 'grid', gap: 6 }}><span>业务事件</span><select data-testid="notification-history-event" style={input} value={historyFilters.eventType} onChange={(event) => setHistoryFilters((prev) => ({ ...prev, eventType: event.target.value }))}><option value="">全部事件</option>{ruleItems.map((item) => <option key={item.event_type} value={item.event_type}>{item.event_label}</option>)}</select></label>
            <label style={{ display: 'grid', gap: 6 }}><span>渠道类型</span><select data-testid="notification-history-channel" style={input} value={historyFilters.channelType} onChange={(event) => setHistoryFilters((prev) => ({ ...prev, channelType: event.target.value }))}><option value="">全部渠道</option>{CHANNEL_TYPES.map((channelType) => <option key={channelType} value={channelType}>{LABELS[channelType]}</option>)}</select></label>
            <label style={{ display: 'grid', gap: 6 }}><span>状态</span><select data-testid="notification-history-status" style={input} value={historyFilters.status} onChange={(event) => setHistoryFilters((prev) => ({ ...prev, status: event.target.value }))}><option value="">全部状态</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'end', flexWrap: 'wrap' }}><button type="button" data-testid="notification-history-apply" style={primaryBtn} onClick={() => applyHistory()}>查询历史</button><button type="button" style={btn} onClick={() => { const next = { eventType: '', channelType: '', status: '' }; setHistoryFilters(next); applyHistory(next); }}>重置</button></div>
          </div>
          <div style={{ overflowX: 'auto', marginTop: 18 }}>
            <table style={table}>
              <thead><tr><th style={cell}>任务 ID</th><th style={cell}>时间</th><th style={cell}>事件</th><th style={cell}>渠道</th><th style={cell}>收件人</th><th style={cell}>状态</th><th style={cell}>错误</th><th style={cell}>操作</th></tr></thead>
              <tbody>
                {historyLoading ? <tr><td style={cell} colSpan={8}>正在加载发送历史...</td></tr> : null}
                {!historyLoading && jobs.length === 0 ? <tr><td style={cell} colSpan={8}>当前没有通知任务。</td></tr> : null}
                {!historyLoading ? jobs.map((job) => <React.Fragment key={job.job_id}><tr><td style={cell}>{job.job_id}</td><td style={cell}>{formatTime(job.created_at_ms)}</td><td style={cell}><div style={{ fontWeight: 600 }}>{eventLabelByType[job.event_type] || job.event_type}</div><div style={muted}>{job.event_type}</div></td><td style={cell}><div>{LABELS[job.channel_type] || job.channel_type || '-'}</div><div style={muted}>{job.channel_name || job.channel_id}</div></td><td style={cell}>{job.recipient_full_name || job.recipient_username || job.recipient_user_id || job.recipient_address || '-'}</td><td style={cell}><span style={{ display: 'inline-flex', borderRadius: 999, padding: '4px 10px', fontWeight: 600, fontSize: '0.82rem', background: job.status === 'sent' ? '#ecfdf5' : job.status === 'failed' ? '#fef2f2' : '#eff6ff', color: job.status === 'sent' ? '#047857' : job.status === 'failed' ? '#b91c1c' : '#1d4ed8' }}>{LABELS[job.status] || job.status}</span></td><td style={cell}>{job.last_error || '-'}</td><td style={cell}><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><button type="button" data-testid={`notification-retry-${job.job_id}`} style={btn} onClick={() => runJobAction(() => notificationApi.retryJob(job.job_id), `任务 ${job.job_id} 已重试`)}>重试</button><button type="button" style={btn} onClick={() => runJobAction(() => notificationApi.resendJob(job.job_id), `任务 ${job.job_id} 已重发`)}>重发</button><button type="button" data-testid={`notification-history-logs-${job.job_id}`} style={btn} onClick={() => toggleLogs(job.job_id)}>{expandedLogs[String(job.job_id)] ? '收起日志' : '查看日志'}</button></div></td></tr>{expandedLogs[String(job.job_id)] ? (logsByJob[String(job.job_id)] || []).map((log) => <tr key={`log-${job.job_id}-${log.id}`}><td style={cell} /><td style={cell} colSpan={7}>[{formatTime(log.attempted_at_ms)}] {log.status}{log.error ? ` - ${log.error}` : ''}</td></tr>) : null}</React.Fragment>) : null}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
