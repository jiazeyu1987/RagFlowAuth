
import React, { useEffect, useState } from 'react';
import { notificationApi } from '../features/notification/api';

const CHANNEL_TYPES = ['email', 'dingtalk', 'in_app'];
const LABELS = {
  email: '\u90ae\u4ef6',
  dingtalk: '\u9489\u9489',
  in_app: '\u7ad9\u5185\u4fe1',
  queued: '\u5f85\u53d1\u9001',
  sent: '\u5df2\u53d1\u9001',
  failed: '\u5931\u8d25',
};
const STATUS_LABELS = {
  queued: LABELS.queued,
  sent: LABELS.sent,
  failed: LABELS.failed,
};
const DEFAULTS = {
  email: { channelId: 'email-main', name: '\u90ae\u4ef6\u901a\u77e5', enabled: false },
  dingtalk: { channelId: 'dingtalk-main', name: '\u9489\u9489\u5de5\u4f5c\u901a\u77e5', enabled: false },
  in_app: { channelId: 'inapp-main', name: '\u7ad9\u5185\u4fe1', enabled: true },
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
  if (!Number.isInteger(parsed)) throw new Error(`${label} \u5fc5\u987b\u662f\u6574\u6570`);
  return parsed;
};

const clean = (value) => Object.fromEntries(Object.entries(value || {}).filter(([, item]) => item !== '' && item !== undefined && item !== null));
const flattenRules = (groups) => (groups || []).flatMap((group) => (group.items || []).map((item) => ({ ...item, group_key: group.group_key })));
const warningText = (item) => {
  const missing = (item.enabled_channel_types || []).filter((channelType) => !(item.has_enabled_channel_config_by_type || {})[channelType]);
  return missing.length ? `\u5df2\u52fe\u9009\u4f46\u672a\u914d\u7f6e\u542f\u7528\u6e20\u9053\uff1a${missing.map((channelType) => LABELS[channelType] || channelType).join('\u3001')}` : '';
};

const buildBuckets = (items) => {
  const buckets = { email: [], dingtalk: [], in_app: [] };
  (items || []).forEach((item) => {
    const channelType = String(item?.channel_type || '').trim().toLowerCase();
    if (buckets[channelType]) buckets[channelType].push(item);
  });
  return buckets;
};

const emptyForms = () => ({
  email: { ...DEFAULTS.email, host: '', port: '', username: '', password: '', use_tls: true, from_email: '', updated_at_ms: null },
  dingtalk: { ...DEFAULTS.dingtalk, app_key: '', app_secret: '', agent_id: '', recipient_map_text: '{\n  "user_id_or_username": "dingtalk_userid"\n}', api_base: '', oapi_base: '', timeout_seconds: '', updated_at_ms: null },
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
    forms.dingtalk = {
      channelId: ding.channel_id || DEFAULTS.dingtalk.channelId,
      name: ding.name || DEFAULTS.dingtalk.name,
      enabled: !!ding.enabled,
      app_key: String(config.app_key || ''),
      app_secret: String(config.app_secret || ''),
      agent_id: config.agent_id === undefined || config.agent_id === null ? '' : String(config.agent_id),
      recipient_map_text: JSON.stringify(config.recipient_map || {}, null, 2),
      api_base: String(config.api_base || ''),
      oapi_base: String(config.oapi_base || ''),
      timeout_seconds: config.timeout_seconds === undefined || config.timeout_seconds === null ? '' : String(config.timeout_seconds),
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
      setError(requestError?.message || '\u52a0\u8f7d\u901a\u77e5\u8bbe\u7f6e\u5931\u8d25');
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
            config: clean({ host: String(email.host || '').trim(), port: toInt(email.port, '\u90ae\u4ef6\u7aef\u53e3'), username: String(email.username || '').trim(), password: String(email.password || ''), use_tls: !!email.use_tls, from_email: String(email.from_email || '').trim() }),
          },
        });
      }
      const ding = forms.dingtalk;
      if (channelBuckets.dingtalk.length > 0 || ding.enabled || ['app_key', 'app_secret', 'agent_id', 'api_base', 'oapi_base', 'timeout_seconds'].some((field) => String(ding[field] || '').trim())) {
        let recipientMap = {};
        try { recipientMap = JSON.parse(String(ding.recipient_map_text || '{}')); } catch { throw new Error('\u9489\u9489 recipient_map \u5fc5\u987b\u662f\u5408\u6cd5 JSON'); }
        if (recipientMap === null || Array.isArray(recipientMap) || typeof recipientMap !== 'object') throw new Error('\u9489\u9489 recipient_map \u5fc5\u987b\u662f\u5bf9\u8c61');
        requests.push({
          channelId: ding.channelId,
          payload: {
            channel_type: 'dingtalk',
            name: ding.name,
            enabled: !!ding.enabled,
            config: clean({ app_key: String(ding.app_key || '').trim(), app_secret: String(ding.app_secret || ''), agent_id: String(ding.agent_id || '').trim(), recipient_map: recipientMap, api_base: String(ding.api_base || '').trim(), oapi_base: String(ding.oapi_base || '').trim(), timeout_seconds: toInt(ding.timeout_seconds, '\u9489\u9489\u8d85\u65f6\u65f6\u95f4') }),
          },
        });
      }
      requests.push({ channelId: forms.in_app.channelId, payload: { channel_type: 'in_app', name: forms.in_app.name, enabled: !!forms.in_app.enabled, config: {} } });
    } catch (requestError) {
      setError(requestError?.message || '\u57fa\u7840\u6e20\u9053\u914d\u7f6e\u6821\u9a8c\u5931\u8d25');
      return;
    }
    setChannelsSaving(true);
    try {
      for (const item of requests) await notificationApi.upsertChannel(item.channelId, item.payload);
      setNotice('\u57fa\u7840\u6e20\u9053\u914d\u7f6e\u5df2\u4fdd\u5b58');
      await loadPage({ keepNotice: true });
    } catch (requestError) {
      setError(requestError?.message || '\u4fdd\u5b58\u57fa\u7840\u6e20\u9053\u914d\u7f6e\u5931\u8d25');
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
      setNotice('\u901a\u77e5\u89c4\u5219\u5df2\u4fdd\u5b58');
    } catch (requestError) {
      setError(requestError?.message || '\u4fdd\u5b58\u901a\u77e5\u89c4\u5219\u5931\u8d25');
    } finally {
      setRulesSaving(false);
    }
  };

  const applyHistory = async (filters = historyFilters) => {
    setError('');
    try { await loadHistory(filters); } catch (requestError) { setError(requestError?.message || '\u52a0\u8f7d\u53d1\u9001\u5386\u53f2\u5931\u8d25'); }
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
      setError(requestError?.message || '\u52a0\u8f7d\u4efb\u52a1\u65e5\u5fd7\u5931\u8d25');
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
      setError(requestError?.message || '\u901a\u77e5\u4efb\u52a1\u64cd\u4f5c\u5931\u8d25');
    }
  };

  const dispatchPending = async () => {
    setDispatching(true);
    await runJobAction(() => notificationApi.dispatchPending(100), '\u5f85\u53d1\u9001\u4efb\u52a1\u5df2\u89e6\u53d1\u5206\u53d1');
    setDispatching(false);
  };

  if (loading) return <div style={{ padding: 12 }}>\u6b63\u5728\u52a0\u8f7d\u901a\u77e5\u8bbe\u7f6e...</div>;

  const renderChannelCard = (channelType) => {
    const form = forms[channelType];
    const duplicates = channelBuckets[channelType] || [];
    return (
      <div key={channelType} style={{ border: '1px solid #e5e7eb', borderRadius: 14, padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 700 }}>{LABELS[channelType]}</div>
            <div style={{ ...muted, marginTop: 4 }}>
              {channelType === 'in_app' ? '\u7cfb\u7edf\u5185\u7f6e\u6d88\u606f\u4e2d\u5fc3\u6e20\u9053\u3002' : channelType === 'email' ? '\u7528\u4e8e SMTP \u90ae\u4ef6\u901a\u77e5\u3002' : '\u7528\u4e8e\u9489\u9489\u4f01\u4e1a\u5e94\u7528\u5de5\u4f5c\u901a\u77e5\u3002'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}><input type="checkbox" checked={!!form.enabled} onChange={(event) => setFormValue(channelType, 'enabled', event.target.checked)} /><span>\u542f\u7528</span></label>
            <span style={muted}>\u6e20\u9053 ID\uff1a{form.channelId}</span>
            <span style={muted}>\u6700\u8fd1\u66f4\u65b0\uff1a{formatTime(form.updated_at_ms)}</span>
          </div>
        </div>
        {duplicates.length > 1 ? <div style={{ marginTop: 10, color: '#92400e', fontSize: '0.88rem' }}>\u5f53\u524d\u5b58\u5728 {duplicates.length} \u4e2a{LABELS[channelType]}\u6e20\u9053\uff0c\u672c\u9875\u53ea\u7f16\u8f91\u6700\u8fd1\u66f4\u65b0\u7684\u4e00\u4e2a\uff1a{form.channelId}</div> : null}
        {channelType === 'email' ? <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 14 }}><label style={{ display: 'grid', gap: 6 }}><span>SMTP \u4e3b\u673a</span><input data-testid="notification-email-host" style={input} value={form.host} onChange={(event) => setFormValue('email', 'host', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>\u7aef\u53e3</span><input data-testid="notification-email-port" style={input} value={form.port} onChange={(event) => setFormValue('email', 'port', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>\u7528\u6237\u540d</span><input data-testid="notification-email-username" style={input} value={form.username} onChange={(event) => setFormValue('email', 'username', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>\u5bc6\u7801</span><input data-testid="notification-email-password" type="password" style={input} value={form.password} onChange={(event) => setFormValue('email', 'password', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>\u53d1\u4ef6\u4eba\u90ae\u7bb1</span><input data-testid="notification-email-from-email" style={input} value={form.from_email} onChange={(event) => setFormValue('email', 'from_email', event.target.value)} /></label><label style={{ display: 'inline-flex', gap: 8, alignItems: 'center', marginTop: 28 }}><input data-testid="notification-email-use-tls" type="checkbox" checked={!!form.use_tls} onChange={(event) => setFormValue('email', 'use_tls', event.target.checked)} /><span>\u542f\u7528 TLS</span></label></div> : null}
        {channelType === 'dingtalk' ? <div style={{ display: 'grid', gap: 12, marginTop: 14 }}><div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}><label style={{ display: 'grid', gap: 6 }}><span>App Key</span><input data-testid="notification-dingtalk-app-key" style={input} value={form.app_key} onChange={(event) => setFormValue('dingtalk', 'app_key', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>App Secret</span><input data-testid="notification-dingtalk-app-secret" type="password" style={input} value={form.app_secret} onChange={(event) => setFormValue('dingtalk', 'app_secret', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>Agent ID</span><input data-testid="notification-dingtalk-agent-id" style={input} value={form.agent_id} onChange={(event) => setFormValue('dingtalk', 'agent_id', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>API Base</span><input style={input} value={form.api_base} placeholder="https://api.dingtalk.com" onChange={(event) => setFormValue('dingtalk', 'api_base', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>OAPI Base</span><input style={input} value={form.oapi_base} placeholder="https://oapi.dingtalk.com" onChange={(event) => setFormValue('dingtalk', 'oapi_base', event.target.value)} /></label><label style={{ display: 'grid', gap: 6 }}><span>\u8d85\u65f6\u65f6\u95f4\uff08\u79d2\uff09</span><input style={input} value={form.timeout_seconds} onChange={(event) => setFormValue('dingtalk', 'timeout_seconds', event.target.value)} /></label></div><label style={{ display: 'grid', gap: 6 }}><span>recipient_map\uff08JSON\uff09</span><textarea data-testid="notification-dingtalk-recipient-map" style={{ ...input, minHeight: 120, fontFamily: 'monospace', resize: 'vertical' }} value={form.recipient_map_text} onChange={(event) => setFormValue('dingtalk', 'recipient_map_text', event.target.value)} /></label></div> : null}
        {channelType === 'in_app' ? <div style={{ ...muted, marginTop: 14 }}>\u7ad9\u5185\u4fe1\u6e20\u9053\u914d\u7f6e\u56fa\u5b9a\u4e3a <code>{'{}'}</code>\u3002</div> : null}
      </div>
    );
  };
  return (
    <div style={{ maxWidth: 1280, display: 'grid', gap: 16 }} data-testid="notification-settings-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0 }}>\u901a\u77e5\u8bbe\u7f6e</h2>
          <div style={{ ...muted, marginTop: 6 }}>\u5148\u914d\u7f6e\u6e20\u9053\u53c2\u6570\uff0c\u518d\u6309\u4e1a\u52a1\u4e8b\u4ef6\u52fe\u9009\u90ae\u4ef6\u3001\u9489\u9489\u3001\u7ad9\u5185\u4fe1\u3002</div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" data-testid="notification-tab-rules" style={activeTab === 'rules' ? primaryBtn : btn} onClick={() => setActiveTab('rules')}>\u901a\u77e5\u89c4\u5219</button>
          <button type="button" data-testid="notification-tab-history" style={activeTab === 'history' ? primaryBtn : btn} onClick={() => setActiveTab('history')}>\u53d1\u9001\u5386\u53f2</button>
        </div>
      </div>
      {error ? <div data-testid="notification-error" style={{ ...card, borderColor: '#fecaca', background: '#fef2f2', color: '#b91c1c' }}>{error}</div> : null}
      {notice ? <div style={{ ...card, borderColor: '#bbf7d0', background: '#f0fdf4', color: '#166534' }}>{notice}</div> : null}

      {activeTab === 'rules' ? (
        <>
          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0 }}>\u57fa\u7840\u6e20\u9053\u914d\u7f6e</h3>
                <div style={{ ...muted, marginTop: 6 }}>\u9489\u9489 recipient_map \u7684 value \u5fc5\u987b\u662f\u9489\u9489 userId\u3002</div>
              </div>
              <button type="button" data-testid="notification-save-channels" style={primaryBtn} onClick={saveChannels} disabled={channelsSaving}>{channelsSaving ? '\u4fdd\u5b58\u4e2d...' : '\u4fdd\u5b58\u57fa\u7840\u6e20\u9053\u914d\u7f6e'}</button>
            </div>
            <div style={{ display: 'grid', gap: 14, marginTop: 16 }}>{CHANNEL_TYPES.map(renderChannelCard)}</div>
          </div>

          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0 }}>\u901a\u77e5\u89c4\u5219</h3>
                <div style={{ ...muted, marginTop: 6 }}>\u6bcf\u4e2a\u4e8b\u4ef6\u53ef\u4ee5\u5355\u9009\u3001\u591a\u9009\uff0c\u4e5f\u53ef\u4ee5\u5168\u90e8\u4e0d\u9009\u3002</div>
              </div>
              <button type="button" data-testid="notification-save-rules" style={primaryBtn} onClick={saveRules} disabled={rulesSaving}>{rulesSaving ? '\u4fdd\u5b58\u4e2d...' : '\u4fdd\u5b58\u901a\u77e5\u89c4\u5219'}</button>
            </div>
            <div style={{ display: 'grid', gap: 16, marginTop: 16 }}>
              {(rulesGroups || []).map((group) => (
                <div key={group.group_key} style={{ border: '1px solid #e5e7eb', borderRadius: 14, overflow: 'hidden' }}>
                  <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', background: '#f9fafb', fontWeight: 700 }}>{group.group_label}</div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={table}>
                      <thead><tr><th style={cell}>\u4e8b\u4ef6</th><th style={cell}>\u90ae\u4ef6</th><th style={cell}>\u9489\u9489</th><th style={cell}>\u7ad9\u5185\u4fe1</th><th style={cell}>\u98ce\u9669\u63d0\u793a</th></tr></thead>
                      <tbody>
                        {(group.items || []).map((item) => (
                          <tr key={item.event_type}>
                            <td style={cell}><div style={{ fontWeight: 600 }}>{item.event_label}</div><div style={muted}>{item.event_type}</div></td>
                            {CHANNEL_TYPES.map((channelType) => <td key={`${item.event_type}-${channelType}`} style={cell}><label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}><input type="checkbox" data-testid={`notification-rule-${item.event_type}-${channelType}`} checked={(item.enabled_channel_types || []).includes(channelType)} onChange={() => toggleRule(item.event_type, channelType)} /><span>{LABELS[channelType]}</span></label></td>)}
                            <td style={cell}>{warningText(item) ? <span style={{ color: '#92400e' }}>{warningText(item)}</span> : <span style={{ color: '#047857' }}>\u5df2\u914d\u7f6e</span>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0 }}>\u53d1\u9001\u5386\u53f2</h3>
              <div style={{ ...muted, marginTop: 6 }}>\u67e5\u770b\u901a\u77e5\u4efb\u52a1\u3001\u6295\u9012\u65e5\u5fd7\uff0c\u5e76\u652f\u6301\u91cd\u8bd5\u3001\u91cd\u53d1\u4e0e\u624b\u52a8\u5206\u53d1\u3002</div>
            </div>
            <button type="button" data-testid="notification-dispatch-pending" style={btn} onClick={dispatchPending} disabled={dispatching}>{dispatching ? '\u5206\u53d1\u4e2d...' : '\u5206\u53d1\u5f85\u5904\u7406\u4efb\u52a1'}</button>
          </div>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 16 }}>
            <label style={{ display: 'grid', gap: 6 }}><span>\u4e1a\u52a1\u4e8b\u4ef6</span><select data-testid="notification-history-event" style={input} value={historyFilters.eventType} onChange={(event) => setHistoryFilters((prev) => ({ ...prev, eventType: event.target.value }))}><option value="">\u5168\u90e8\u4e8b\u4ef6</option>{ruleItems.map((item) => <option key={item.event_type} value={item.event_type}>{item.event_label}</option>)}</select></label>
            <label style={{ display: 'grid', gap: 6 }}><span>\u6e20\u9053\u7c7b\u578b</span><select data-testid="notification-history-channel" style={input} value={historyFilters.channelType} onChange={(event) => setHistoryFilters((prev) => ({ ...prev, channelType: event.target.value }))}><option value="">\u5168\u90e8\u6e20\u9053</option>{CHANNEL_TYPES.map((channelType) => <option key={channelType} value={channelType}>{LABELS[channelType]}</option>)}</select></label>
            <label style={{ display: 'grid', gap: 6 }}><span>\u72b6\u6001</span><select data-testid="notification-history-status" style={input} value={historyFilters.status} onChange={(event) => setHistoryFilters((prev) => ({ ...prev, status: event.target.value }))}><option value="">\u5168\u90e8\u72b6\u6001</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'end', flexWrap: 'wrap' }}><button type="button" data-testid="notification-history-apply" style={primaryBtn} onClick={() => applyHistory()}>\u67e5\u8be2\u5386\u53f2</button><button type="button" style={btn} onClick={() => { const next = { eventType: '', channelType: '', status: '' }; setHistoryFilters(next); applyHistory(next); }}>\u91cd\u7f6e</button></div>
          </div>
          <div style={{ overflowX: 'auto', marginTop: 18 }}>
            <table style={table}>
              <thead><tr><th style={cell}>\u4efb\u52a1 ID</th><th style={cell}>\u65f6\u95f4</th><th style={cell}>\u4e8b\u4ef6</th><th style={cell}>\u6e20\u9053</th><th style={cell}>\u6536\u4ef6\u4eba</th><th style={cell}>\u72b6\u6001</th><th style={cell}>\u9519\u8bef</th><th style={cell}>\u64cd\u4f5c</th></tr></thead>
              <tbody>
                {historyLoading ? <tr><td style={cell} colSpan={8}>\u6b63\u5728\u52a0\u8f7d\u53d1\u9001\u5386\u53f2...</td></tr> : null}
                {!historyLoading && jobs.length === 0 ? <tr><td style={cell} colSpan={8}>\u5f53\u524d\u6ca1\u6709\u901a\u77e5\u4efb\u52a1\u3002</td></tr> : null}
                {!historyLoading ? jobs.map((job) => <React.Fragment key={job.job_id}><tr><td style={cell}>{job.job_id}</td><td style={cell}>{formatTime(job.created_at_ms)}</td><td style={cell}><div style={{ fontWeight: 600 }}>{eventLabelByType[job.event_type] || job.event_type}</div><div style={muted}>{job.event_type}</div></td><td style={cell}><div>{LABELS[job.channel_type] || job.channel_type || '-'}</div><div style={muted}>{job.channel_name || job.channel_id}</div></td><td style={cell}>{job.recipient_username || job.recipient_user_id || job.recipient_address || '-'}</td><td style={cell}><span style={{ display: 'inline-flex', borderRadius: 999, padding: '4px 10px', fontWeight: 600, fontSize: '0.82rem', background: job.status === 'sent' ? '#ecfdf5' : job.status === 'failed' ? '#fef2f2' : '#eff6ff', color: job.status === 'sent' ? '#047857' : job.status === 'failed' ? '#b91c1c' : '#1d4ed8' }}>{LABELS[job.status] || job.status}</span></td><td style={cell}>{job.last_error || '-'}</td><td style={cell}><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><button type="button" data-testid={`notification-retry-${job.job_id}`} style={btn} onClick={() => runJobAction(() => notificationApi.retryJob(job.job_id), `\u4efb\u52a1 ${job.job_id} \u5df2\u91cd\u8bd5`)}>\u91cd\u8bd5</button><button type="button" style={btn} onClick={() => runJobAction(() => notificationApi.resendJob(job.job_id), `\u4efb\u52a1 ${job.job_id} \u5df2\u91cd\u53d1`)}>\u91cd\u53d1</button><button type="button" data-testid={`notification-history-logs-${job.job_id}`} style={btn} onClick={() => toggleLogs(job.job_id)}>{expandedLogs[String(job.job_id)] ? '\u6536\u8d77\u65e5\u5fd7' : '\u67e5\u770b\u65e5\u5fd7'}</button></div></td></tr>{expandedLogs[String(job.job_id)] ? (logsByJob[String(job.job_id)] || []).map((log) => <tr key={`log-${job.job_id}-${log.id}`}><td style={cell} /><td style={cell} colSpan={7}>[{formatTime(log.attempted_at_ms)}] {log.status}{log.error ? ` - ${log.error}` : ''}</td></tr>) : null}</React.Fragment>) : null}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
