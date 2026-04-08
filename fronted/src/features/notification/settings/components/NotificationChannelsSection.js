import React from 'react';
import { card, input, muted, primaryBtn } from '../pageStyles';

function ChannelCard({
  channelType,
  labels,
  descriptions,
  form,
  duplicates,
  onChange,
  formatTime,
}) {
  return (
    <div key={channelType} style={{ border: '1px solid #e5e7eb', borderRadius: 14, padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontWeight: 700 }}>{labels[channelType]}</div>
          <div style={{ ...muted, marginTop: 4 }}>{descriptions[channelType]}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={!!form.enabled}
              onChange={(event) => onChange(channelType, 'enabled', event.target.checked)}
            />
            <span>启用</span>
          </label>
          <span style={muted}>通道 ID：{form.channelId}</span>
          <span style={muted}>更新时间：{formatTime(form.updated_at_ms)}</span>
        </div>
      </div>
      {duplicates.length > 1 ? (
        <div style={{ marginTop: 10, color: '#92400e', fontSize: '0.88rem' }}>
          当前存在 {duplicates.length} 个{labels[channelType]}通道，本页编辑的是最新一条：{form.channelId}
        </div>
      ) : null}
      {channelType === 'email' ? (
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 14 }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>SMTP 主机</span>
            <input
              data-testid="notification-email-host"
              style={input}
              value={form.host}
              onChange={(event) => onChange('email', 'host', event.target.value)}
            />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>端口</span>
            <input
              data-testid="notification-email-port"
              style={input}
              value={form.port}
              onChange={(event) => onChange('email', 'port', event.target.value)}
            />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>用户名</span>
            <input
              data-testid="notification-email-username"
              style={input}
              value={form.username}
              onChange={(event) => onChange('email', 'username', event.target.value)}
            />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>密码</span>
            <input
              data-testid="notification-email-password"
              type="password"
              style={input}
              value={form.password}
              onChange={(event) => onChange('email', 'password', event.target.value)}
            />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>发件邮箱</span>
            <input
              data-testid="notification-email-from-email"
              style={input}
              value={form.from_email}
              onChange={(event) => onChange('email', 'from_email', event.target.value)}
            />
          </label>
          <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center', marginTop: 28 }}>
            <input
              data-testid="notification-email-use-tls"
              type="checkbox"
              checked={!!form.use_tls}
              onChange={(event) => onChange('email', 'use_tls', event.target.checked)}
            />
            <span>启用 TLS</span>
          </label>
        </div>
      ) : null}
      {channelType === 'dingtalk' ? (
        <div style={{ display: 'grid', gap: 12, marginTop: 14 }}>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <label style={{ display: 'grid', gap: 6 }}>
              <span>应用 Key</span>
              <input
                data-testid="notification-dingtalk-app-key"
                style={input}
                value={form.app_key}
                onChange={(event) => onChange('dingtalk', 'app_key', event.target.value)}
              />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span>应用 Secret</span>
              <input
                data-testid="notification-dingtalk-app-secret"
                type="password"
                style={input}
                value={form.app_secret}
                onChange={(event) => onChange('dingtalk', 'app_secret', event.target.value)}
              />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span>Agent ID</span>
              <input
                data-testid="notification-dingtalk-agent-id"
                style={input}
                value={form.agent_id}
                onChange={(event) => onChange('dingtalk', 'agent_id', event.target.value)}
              />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span>API 地址</span>
              <input
                style={input}
                value={form.api_base}
                placeholder="https://api.dingtalk.com"
                onChange={(event) => onChange('dingtalk', 'api_base', event.target.value)}
              />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span>OAPI 地址</span>
              <input
                style={input}
                value={form.oapi_base}
                placeholder="https://oapi.dingtalk.com"
                onChange={(event) => onChange('dingtalk', 'oapi_base', event.target.value)}
              />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span>超时时间（秒）</span>
              <input
                style={input}
                value={form.timeout_seconds}
                onChange={(event) => onChange('dingtalk', 'timeout_seconds', event.target.value)}
              />
            </label>
          </div>
          <label style={{ display: 'grid', gap: 6 }}>
            <span>recipient_map（JSON）</span>
            <textarea
              data-testid="notification-dingtalk-recipient-map"
              style={{ ...input, minHeight: 120, fontFamily: 'monospace', resize: 'vertical' }}
              value={form.recipient_map_text}
              onChange={(event) => onChange('dingtalk', 'recipient_map_text', event.target.value)}
            />
          </label>
        </div>
      ) : null}
      {channelType === 'in_app' ? (
        <div style={{ ...muted, marginTop: 14 }}>
          站内信通道配置固定为 <code>{'{}'}</code>。
        </div>
      ) : null}
    </div>
  );
}

export default function NotificationChannelsSection({
  title,
  description,
  channelTypes,
  labels,
  descriptions,
  forms,
  channelBuckets,
  channelsSaving,
  onSave,
  onChange,
  formatTime,
}) {
  return (
    <div style={card}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSave();
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0 }}>{title}</h3>
            <div style={{ ...muted, marginTop: 6 }}>{description}</div>
          </div>
          <button
            type="submit"
            data-testid="notification-save-channels"
            style={primaryBtn}
            disabled={channelsSaving}
          >
            {channelsSaving ? '保存中...' : '保存通知通道'}
          </button>
        </div>
        <div style={{ display: 'grid', gap: 14, marginTop: 16 }}>
          {channelTypes.map((channelType) => (
            <ChannelCard
              key={channelType}
              channelType={channelType}
              labels={labels}
              descriptions={descriptions}
              form={forms[channelType]}
              duplicates={channelBuckets[channelType] || []}
              onChange={onChange}
              formatTime={formatTime}
            />
          ))}
        </div>
      </form>
    </div>
  );
}
