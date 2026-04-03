import React, { useEffect, useState } from 'react';
import { notificationApi } from '../features/notification/api';

const cardStyle = {
  background: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '16px',
  marginTop: '16px',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

const thtdStyle = {
  borderBottom: '1px solid #e5e7eb',
  textAlign: 'left',
  padding: '8px',
  verticalAlign: 'top',
  fontSize: '0.9rem',
};

const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  background: 'white',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

const primaryButtonStyle = {
  ...buttonStyle,
  border: 'none',
  background: '#2563eb',
  color: 'white',
};

const TEXT = {
  defaultChannelName: '\u4e3b\u90ae\u7bb1',
  loadError: '\u52a0\u8f7d\u901a\u77e5\u6570\u636e\u5931\u8d25',
  invalidJson: '\u6e20\u9053\u914d\u7f6e\u5fc5\u987b\u662f\u6709\u6548\u7684 JSON',
  saveChannelError: '\u4fdd\u5b58\u6e20\u9053\u5931\u8d25',
  dispatchError: '\u5206\u53d1\u5f85\u5904\u7406\u4efb\u52a1\u5931\u8d25',
  retryError: '\u91cd\u8bd5\u901a\u77e5\u4efb\u52a1\u5931\u8d25',
  loadLogsError: '\u52a0\u8f7d\u4efb\u52a1\u65e5\u5fd7\u5931\u8d25',
  loading: '\u6b63\u5728\u52a0\u8f7d\u901a\u77e5\u8bbe\u7f6e...',
  pageTitle: '\u901a\u77e5\u8bbe\u7f6e',
  dispatching: '\u5206\u53d1\u4e2d...',
  dispatchPending: '\u5206\u53d1\u5f85\u5904\u7406\u4efb\u52a1',
  channelConfig: '\u6e20\u9053\u914d\u7f6e',
  channelId: '\u6e20\u9053 ID',
  channelName: '\u6e20\u9053\u540d\u79f0',
  channelNamePlaceholder: '\u4e3b\u90ae\u7bb1',
  channelType: '\u6e20\u9053\u7c7b\u578b',
  enabled: '\u542f\u7528',
  configJson: '\u914d\u7f6e\uff08JSON\uff09',
  saving: '\u4fdd\u5b58\u4e2d...',
  saveChannel: '\u4fdd\u5b58\u6e20\u9053',
  configuredChannels: '\u5df2\u914d\u7f6e\u6e20\u9053',
  type: '\u7c7b\u578b',
  name: '\u540d\u79f0',
  updatedAt: '\u66f4\u65b0\u65f6\u95f4',
  noChannels: '\u6682\u65e0\u5df2\u914d\u7f6e\u6e20\u9053',
  yes: '\u662f',
  no: '\u5426',
  notificationJobs: '\u901a\u77e5\u4efb\u52a1',
  jobId: '\u4efb\u52a1 ID',
  channel: '\u6e20\u9053',
  event: '\u4e8b\u4ef6',
  status: '\u72b6\u6001',
  attempts: '\u5c1d\u8bd5\u6b21\u6570',
  lastError: '\u6700\u540e\u9519\u8bef',
  createdAt: '\u521b\u5efa\u65f6\u95f4',
  actions: '\u64cd\u4f5c',
  noJobs: '\u6682\u65e0\u901a\u77e5\u4efb\u52a1',
  retry: '\u91cd\u8bd5',
  logs: '\u65e5\u5fd7',
  dingtalkRecipientMapHint:
    '\u9489\u9489\u5de5\u4f5c\u901a\u77e5\uff1arecipient_map \u7684 value \u5fc5\u987b\u662f\u9489\u9489 userId\uff0ckey \u53ef\u4f7f\u7528 user_id \u6216 username\u3002',
};

const DEFAULT_EMAIL_CONFIG_TEXT = '{\n  "to_emails": ["qa@example.com"]\n}';
const DEFAULT_DINGTALK_CONFIG_TEXT = '{\n  "app_key": "your_app_key",\n  "app_secret": "your_app_secret",\n  "agent_id": "4432005762",\n  "recipient_map": {\n    "user_id_or_username": "dingtalk_userid"\n  }\n}';
const DEFAULT_IN_APP_CONFIG_TEXT = '{}';

const DEFAULT_CONFIG_TEXT_BY_CHANNEL_TYPE = {
  email: DEFAULT_EMAIL_CONFIG_TEXT,
  dingtalk: DEFAULT_DINGTALK_CONFIG_TEXT,
  in_app: DEFAULT_IN_APP_CONFIG_TEXT,
};

const formatTime = (ms) => {
  if (!ms) return '-';
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) return '-';
  return new Date(n).toLocaleString();
};

const NotificationSettings = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [error, setError] = useState('');
  const [channels, setChannels] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [logsByJob, setLogsByJob] = useState({});

  const [channelId, setChannelId] = useState('email-main');
  const [channelType, setChannelType] = useState('email');
  const [channelName, setChannelName] = useState(TEXT.defaultChannelName);
  const [channelEnabled, setChannelEnabled] = useState(true);
  const [configText, setConfigText] = useState(DEFAULT_EMAIL_CONFIG_TEXT);

  const loadData = async () => {
    setError('');
    setLoading(true);
    try {
      const [channelResp, jobsResp] = await Promise.all([
        notificationApi.listChannels(false),
        notificationApi.listJobs({ limit: 100 }),
      ]);
      setChannels(channelResp.items || []);
      setJobs(jobsResp.items || []);
    } catch (e) {
      setError(e.message || TEXT.loadError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveChannel = async () => {
    setError('');
    let parsedConfig = {};
    try {
      parsedConfig = configText.trim() ? JSON.parse(configText) : {};
    } catch {
      setError(TEXT.invalidJson);
      return;
    }
    setSaving(true);
    try {
      await notificationApi.upsertChannel(channelId.trim(), {
        channel_type: channelType,
        name: channelName.trim(),
        enabled: channelEnabled,
        config: parsedConfig,
      });
      await loadData();
    } catch (e) {
      setError(e.message || TEXT.saveChannelError);
    } finally {
      setSaving(false);
    }
  };

  const handleDispatchPending = async () => {
    setError('');
    setDispatching(true);
    try {
      await notificationApi.dispatchPending(100);
      await loadData();
    } catch (e) {
      setError(e.message || TEXT.dispatchError);
    } finally {
      setDispatching(false);
    }
  };

  const handleRetry = async (jobId) => {
    setError('');
    try {
      await notificationApi.retryJob(jobId);
      await loadData();
    } catch (e) {
      setError(e.message || TEXT.retryError);
    }
  };

  const handleLoadLogs = async (jobId) => {
    setError('');
    try {
      const res = await notificationApi.listJobLogs(jobId, 20);
      setLogsByJob((prev) => ({ ...prev, [String(jobId)]: res.items || [] }));
    } catch (e) {
      setError(e.message || TEXT.loadLogsError);
    }
  };

  if (loading) {
    return <div style={{ padding: '12px' }}>{TEXT.loading}</div>;
  }

  return (
    <div style={{ maxWidth: '1200px' }} data-testid="notification-settings-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>{TEXT.pageTitle}</h2>
        <button
          type="button"
          data-testid="notification-dispatch-pending"
          onClick={handleDispatchPending}
          disabled={dispatching}
          style={{ ...buttonStyle, cursor: dispatching ? 'not-allowed' : 'pointer' }}
        >
          {dispatching ? TEXT.dispatching : TEXT.dispatchPending}
        </button>
      </div>

      {error ? (
        <div data-testid="notification-error" style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
          {error}
        </div>
      ) : null}

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>{TEXT.channelConfig}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.channelId}</span>
            <input
              data-testid="notification-channel-id"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              placeholder="email-main"
              style={{ padding: '8px', borderRadius: '8px', border: '1px solid #d1d5db' }}
            />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.channelName}</span>
            <input
              data-testid="notification-channel-name"
              value={channelName}
              onChange={(e) => setChannelName(e.target.value)}
              placeholder={TEXT.channelNamePlaceholder}
              style={{ padding: '8px', borderRadius: '8px', border: '1px solid #d1d5db' }}
            />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.channelType}</span>
            <select
              data-testid="notification-channel-type"
              value={channelType}
              onChange={(e) => {
                const nextType = e.target.value;
                setChannelType(nextType);
                setConfigText(DEFAULT_CONFIG_TEXT_BY_CHANNEL_TYPE[nextType] || '{}');
              }}
              style={{ padding: '8px', borderRadius: '8px', border: '1px solid #d1d5db' }}
            >
              <option value="email">email</option>
              <option value="dingtalk">dingtalk</option>
              <option value="in_app">in_app</option>
            </select>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '22px' }}>
            <input
              data-testid="notification-channel-enabled"
              type="checkbox"
              checked={channelEnabled}
              onChange={(e) => setChannelEnabled(e.target.checked)}
            />
            <span>{TEXT.enabled}</span>
          </label>
        </div>
        <div style={{ marginTop: '12px' }}>
          <label style={{ display: 'grid', gap: '6px' }}>
            <span>{TEXT.configJson}</span>
            <textarea
              data-testid="notification-channel-config"
              value={configText}
              onChange={(e) => setConfigText(e.target.value)}
              rows={8}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db', fontFamily: 'monospace' }}
            />
          </label>
          {channelType === 'dingtalk' ? (
            <div style={{ marginTop: '8px', color: '#4b5563', fontSize: '0.85rem' }}>
              {TEXT.dingtalkRecipientMapHint}
            </div>
          ) : null}
        </div>
        <div style={{ marginTop: '12px' }}>
          <button
            type="button"
            data-testid="notification-save-channel"
            onClick={handleSaveChannel}
            disabled={saving}
            style={{ ...primaryButtonStyle, cursor: saving ? 'not-allowed' : 'pointer' }}
          >
            {saving ? TEXT.saving : TEXT.saveChannel}
          </button>
        </div>
      </div>

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>{TEXT.configuredChannels}</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thtdStyle}>{TEXT.channelId}</th>
                <th style={thtdStyle}>{TEXT.type}</th>
                <th style={thtdStyle}>{TEXT.name}</th>
                <th style={thtdStyle}>{TEXT.enabled}</th>
                <th style={thtdStyle}>{TEXT.updatedAt}</th>
              </tr>
            </thead>
            <tbody>
              {channels.length === 0 ? (
                <tr>
                  <td style={thtdStyle} colSpan={5}>{TEXT.noChannels}</td>
                </tr>
              ) : channels.map((item) => (
                <tr key={item.channel_id}>
                  <td style={thtdStyle}>{item.channel_id}</td>
                  <td style={thtdStyle}>{item.channel_type}</td>
                  <td style={thtdStyle}>{item.name}</td>
                  <td style={thtdStyle}>{item.enabled ? TEXT.yes : TEXT.no}</td>
                  <td style={thtdStyle}>{formatTime(item.updated_at_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>{TEXT.notificationJobs}</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thtdStyle}>{TEXT.jobId}</th>
                <th style={thtdStyle}>{TEXT.channel}</th>
                <th style={thtdStyle}>{TEXT.event}</th>
                <th style={thtdStyle}>{TEXT.status}</th>
                <th style={thtdStyle}>{TEXT.attempts}</th>
                <th style={thtdStyle}>{TEXT.lastError}</th>
                <th style={thtdStyle}>{TEXT.createdAt}</th>
                <th style={thtdStyle}>{TEXT.actions}</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 ? (
                <tr>
                  <td style={thtdStyle} colSpan={8}>{TEXT.noJobs}</td>
                </tr>
              ) : jobs.map((job) => (
                <React.Fragment key={job.job_id}>
                  <tr>
                    <td style={thtdStyle}>{job.job_id}</td>
                    <td style={thtdStyle}>{job.channel_id}</td>
                    <td style={thtdStyle}>{job.event_type}</td>
                    <td style={thtdStyle}>{job.status}</td>
                    <td style={thtdStyle}>{job.attempts}/{job.max_attempts}</td>
                    <td style={thtdStyle}>{job.last_error || '-'}</td>
                    <td style={thtdStyle}>{formatTime(job.created_at_ms)}</td>
                    <td style={thtdStyle}>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <button
                          type="button"
                          data-testid={`notification-retry-${job.job_id}`}
                          onClick={() => handleRetry(job.job_id)}
                          style={buttonStyle}
                        >
                          {TEXT.retry}
                        </button>
                        <button
                          type="button"
                          data-testid={`notification-logs-${job.job_id}`}
                          onClick={() => handleLoadLogs(job.job_id)}
                          style={buttonStyle}
                        >
                          {TEXT.logs}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {(logsByJob[String(job.job_id)] || []).map((log) => (
                    <tr key={`log-${log.id}`}>
                      <td style={thtdStyle} />
                      <td style={thtdStyle} colSpan={7}>
                        [{formatTime(log.attempted_at_ms)}] {log.status} {log.error ? `- ${log.error}` : ''}
                      </td>
                    </tr>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default NotificationSettings;
