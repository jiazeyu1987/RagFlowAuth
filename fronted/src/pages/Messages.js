import React from 'react';
import useMessagesPage from '../features/notification/messages/useMessagesPage';

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
  pageTitle: '\u6d88\u606f\u4e2d\u5fc3',
  loading: '\u6b63\u5728\u52a0\u8f7d\u7ad9\u5185\u4fe1...',
  loadError: '\u52a0\u8f7d\u7ad9\u5185\u4fe1\u5931\u8d25',
  markError: '\u66f4\u65b0\u8bfb\u53d6\u72b6\u6001\u5931\u8d25',
  markAllError: '\u5168\u90e8\u6807\u8bb0\u5df2\u8bfb\u5931\u8d25',
  unreadOnly: '\u4ec5\u770b\u672a\u8bfb',
  showAll: '\u67e5\u770b\u5168\u90e8',
  markAllRead: '\u5168\u90e8\u6807\u8bb0\u5df2\u8bfb',
  eventType: '\u4e8b\u4ef6\u7c7b\u578b',
  document: '\u6587\u6863',
  step: '\u6d41\u7a0b\u8282\u70b9',
  createdAt: '\u53d1\u9001\u65f6\u95f4',
  readStatus: '\u72b6\u6001',
  action: '\u64cd\u4f5c',
  read: '\u5df2\u8bfb',
  unread: '\u672a\u8bfb',
  markRead: '\u6807\u8bb0\u5df2\u8bfb',
  markUnread: '\u6807\u8bb0\u672a\u8bfb',
  noMessages: '\u6682\u65e0\u7ad9\u5185\u4fe1',
};

const formatTime = (ms) => {
  if (!ms) return '-';
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) return '-';
  return new Date(n).toLocaleString();
};

const messageDocText = (item) => {
  const payload = item?.payload || {};
  return payload.filename || payload.doc_id || '-';
};

const messageStepText = (item) => {
  const payload = item?.payload || {};
  return payload.current_step_name || '-';
};

const Messages = () => {
  const {
    loading,
    error,
    items,
    total,
    unreadCount,
    unreadOnly,
    busyMap,
    markAllBusy,
    handleToggleUnreadOnly,
    handleToggleRead,
    handleMarkAllRead,
  } = useMessagesPage();

  if (loading) {
    return <div style={{ padding: '12px' }}>{TEXT.loading}</div>;
  }

  return (
    <div style={{ maxWidth: '1200px' }} data-testid="messages-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>{TEXT.pageTitle}</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span data-testid="messages-unread-count">{`\u672a\u8bfb ${unreadCount}`}</span>
          <button
            type="button"
            data-testid="messages-toggle-unread"
            onClick={handleToggleUnreadOnly}
            style={buttonStyle}
          >
            {unreadOnly ? TEXT.showAll : TEXT.unreadOnly}
          </button>
          <button
            type="button"
            data-testid="messages-mark-all-read"
            onClick={handleMarkAllRead}
            disabled={markAllBusy || unreadCount <= 0}
            style={{
              ...primaryButtonStyle,
              cursor: markAllBusy || unreadCount <= 0 ? 'not-allowed' : 'pointer',
              opacity: markAllBusy || unreadCount <= 0 ? 0.7 : 1,
            }}
          >
            {TEXT.markAllRead}
          </button>
        </div>
      </div>

      {error ? (
        <div data-testid="messages-error" style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}>
          {error}
        </div>
      ) : null}

      <div style={cardStyle}>
        <div style={{ marginBottom: '10px' }} data-testid="messages-total">{`\u5171 ${total} \u6761`}</div>
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thtdStyle}>{TEXT.eventType}</th>
                <th style={thtdStyle}>{TEXT.document}</th>
                <th style={thtdStyle}>{TEXT.step}</th>
                <th style={thtdStyle}>{TEXT.createdAt}</th>
                <th style={thtdStyle}>{TEXT.readStatus}</th>
                <th style={thtdStyle}>{TEXT.action}</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td style={thtdStyle} colSpan={6}>{TEXT.noMessages}</td>
                </tr>
              ) : items.map((item) => {
                const rowBusy = !!busyMap[String(item.job_id)];
                const isRead = !!item.read_at_ms;
                return (
                  <tr key={item.job_id} data-testid={`messages-row-${item.job_id}`}>
                    <td style={thtdStyle}>{item.event_type}</td>
                    <td style={thtdStyle}>{messageDocText(item)}</td>
                    <td style={thtdStyle}>{messageStepText(item)}</td>
                    <td style={thtdStyle}>{formatTime(item.created_at_ms)}</td>
                    <td style={thtdStyle}>{isRead ? TEXT.read : TEXT.unread}</td>
                    <td style={thtdStyle}>
                      <button
                        type="button"
                        data-testid={`messages-toggle-read-${item.job_id}`}
                        onClick={() => handleToggleRead(item)}
                        disabled={rowBusy}
                        style={{ ...buttonStyle, cursor: rowBusy ? 'not-allowed' : 'pointer' }}
                      >
                        {isRead ? TEXT.markUnread : TEXT.markRead}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Messages;
