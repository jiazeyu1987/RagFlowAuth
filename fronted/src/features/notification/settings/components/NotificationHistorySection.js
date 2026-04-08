import React from 'react';
import { btn, card, cell, input, muted, primaryBtn, table } from '../pageStyles';

export default function NotificationHistorySection({
  title,
  description,
  dispatching,
  onDispatchPending,
  historyFilters,
  setHistoryFilter,
  applyHistory,
  resetHistoryFilters,
  ruleItems,
  channelTypes,
  labels,
  statusLabels,
  historyLoading,
  jobs,
  logsByJob,
  expandedLogs,
  eventLabelByType,
  formatTime,
  onRetryJob,
  onResendJob,
  onToggleLogs,
}) {
  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <div style={{ ...muted, marginTop: 6 }}>{description}</div>
        </div>
        <button
          type="button"
          data-testid="notification-dispatch-pending"
          style={btn}
          onClick={onDispatchPending}
          disabled={dispatching}
        >
          {dispatching ? '派发中...' : '派发待处理任务'}
        </button>
      </div>

      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginTop: 16 }}>
        <label style={{ display: 'grid', gap: 6 }}>
          <span>事件</span>
          <select
            data-testid="notification-history-event"
            style={input}
            value={historyFilters.eventType}
            onChange={(event) => setHistoryFilter('eventType', event.target.value)}
          >
            <option value="">全部事件</option>
            {ruleItems.map((item) => (
              <option key={item.event_type} value={item.event_type}>
                {item.event_label}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'grid', gap: 6 }}>
          <span>通道类型</span>
          <select
            data-testid="notification-history-channel"
            style={input}
            value={historyFilters.channelType}
            onChange={(event) => setHistoryFilter('channelType', event.target.value)}
          >
            <option value="">全部通道</option>
            {channelTypes.map((channelType) => (
              <option key={channelType} value={channelType}>
                {labels[channelType]}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'grid', gap: 6 }}>
          <span>状态</span>
          <select
            data-testid="notification-history-status"
            style={input}
            value={historyFilters.status}
            onChange={(event) => setHistoryFilter('status', event.target.value)}
          >
            <option value="">全部状态</option>
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <div style={{ display: 'flex', gap: 8, alignItems: 'end', flexWrap: 'wrap' }}>
          <button type="button" data-testid="notification-history-apply" style={primaryBtn} onClick={() => applyHistory()}>
            应用筛选
          </button>
          <button type="button" style={btn} onClick={resetHistoryFilters}>
            重置
          </button>
        </div>
      </div>

      <div style={{ overflowX: 'auto', marginTop: 18 }}>
        <table style={table}>
          <thead>
            <tr>
              <th style={cell}>任务 ID</th>
              <th style={cell}>时间</th>
              <th style={cell}>事件</th>
              <th style={cell}>通道</th>
              <th style={cell}>接收人</th>
              <th style={cell}>状态</th>
              <th style={cell}>错误</th>
              <th style={cell}>操作</th>
            </tr>
          </thead>
          <tbody>
            {historyLoading ? (
              <tr>
                <td style={cell} colSpan={8}>正在加载通知历史...</td>
              </tr>
            ) : null}
            {!historyLoading && jobs.length === 0 ? (
              <tr>
                <td style={cell} colSpan={8}>暂无通知任务。</td>
              </tr>
            ) : null}
            {!historyLoading
              ? jobs.map((job) => (
                <React.Fragment key={job.job_id}>
                  <tr>
                    <td style={cell}>{job.job_id}</td>
                    <td style={cell}>{formatTime(job.created_at_ms)}</td>
                    <td style={cell}>
                      <div style={{ fontWeight: 600 }}>{eventLabelByType[job.event_type] || job.event_type}</div>
                    </td>
                    <td style={cell}>
                      <div>{labels[job.channel_type] || job.channel_type || '-'}</div>
                    </td>
                    <td style={cell}>
                      {job.recipient_full_name || job.recipient_username || job.recipient_user_id || job.recipient_address || '-'}
                    </td>
                    <td style={cell}>
                      <span
                        style={{
                          display: 'inline-flex',
                          borderRadius: 999,
                          padding: '4px 10px',
                          fontWeight: 600,
                          fontSize: '0.82rem',
                          background: job.status === 'sent' ? '#ecfdf5' : job.status === 'failed' ? '#fef2f2' : '#eff6ff',
                          color: job.status === 'sent' ? '#047857' : job.status === 'failed' ? '#b91c1c' : '#1d4ed8',
                        }}
                      >
                        {statusLabels[job.status] || job.status}
                      </span>
                    </td>
                    <td style={cell}>{job.last_error || '-'}</td>
                    <td style={cell}>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <button
                          type="button"
                          data-testid={`notification-retry-${job.job_id}`}
                          style={btn}
                          onClick={() => onRetryJob(job.job_id)}
                        >
                          重试
                        </button>
                        <button type="button" style={btn} onClick={() => onResendJob(job.job_id)}>
                          重发
                        </button>
                        <button
                          type="button"
                          data-testid={`notification-history-logs-${job.job_id}`}
                          style={btn}
                          onClick={() => onToggleLogs(job.job_id)}
                        >
                          {expandedLogs[String(job.job_id)] ? '隐藏日志' : '查看日志'}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedLogs[String(job.job_id)]
                    ? (logsByJob[String(job.job_id)] || []).map((log) => (
                      <tr key={`log-${job.job_id}-${log.id}`}>
                        <td style={cell} />
                        <td style={cell} colSpan={7}>
                          [{formatTime(log.attempted_at_ms)}] {statusLabels[log.status] || log.status}{log.error ? ` - ${log.error}` : ''}
                        </td>
                      </tr>
                    ))
                    : null}
                </React.Fragment>
              ))
              : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
