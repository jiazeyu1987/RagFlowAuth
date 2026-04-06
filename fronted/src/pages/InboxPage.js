import React from 'react';
import useInboxPage from '../features/operationApproval/useInboxPage';

const cardStyle = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '14px',
  padding: '16px',
};

const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '10px',
  background: '#ffffff',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

const primaryButtonStyle = {
  ...buttonStyle,
  background: '#2563eb',
  borderColor: '#2563eb',
  color: '#ffffff',
};

const TEXT = {
  title: '站内信',
  subtitle: '审批流通知会统一进入这里，并可跳转到申请详情。',
  unread: '未读',
  read: '已读',
  unreadPrefix: '未读',
  showAll: '查看全部',
  unreadOnly: '仅看未读',
  markAllRead: '全部标记已读',
  processing: '处理中...',
  loading: '正在加载站内信...',
  empty: '当前没有站内信。',
  viewDetail: '查看详情',
  markRead: '标记已读',
};

export default function InboxPage() {
  const {
    loading,
    error,
    items,
    unreadOnly,
    unreadCount,
    busyId,
    markAllBusy,
    toggleUnreadOnly,
    handleMarkRead,
    handleOpen,
    handleMarkAllRead,
  } = useInboxPage();

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="inbox-page">
      <div
        style={{
          ...cardStyle,
          display: 'flex',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>{TEXT.title}</div>
          <div style={{ color: '#4b5563', marginTop: '4px' }}>{TEXT.subtitle}</div>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span data-testid="inbox-unread-count">{`${TEXT.unreadPrefix} ${unreadCount}`}</span>
          <button
            type="button"
            data-testid="inbox-toggle-unread"
            onClick={toggleUnreadOnly}
            style={buttonStyle}
          >
            {unreadOnly ? TEXT.showAll : TEXT.unreadOnly}
          </button>
          <button
            type="button"
            data-testid="inbox-mark-all-read"
            onClick={handleMarkAllRead}
            disabled={markAllBusy || unreadCount <= 0}
            style={primaryButtonStyle}
          >
            {markAllBusy ? TEXT.processing : TEXT.markAllRead}
          </button>
        </div>
      </div>

      {error ? (
        <div
          data-testid="inbox-error"
          style={{
            ...cardStyle,
            borderColor: '#fecaca',
            background: '#fef2f2',
            color: '#991b1b',
          }}
        >
          {error}
        </div>
      ) : null}

      <div style={cardStyle}>
        {loading ? (
          <div>{TEXT.loading}</div>
        ) : items.length === 0 ? (
          <div style={{ color: '#6b7280' }}>{TEXT.empty}</div>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {items.map((item) => {
              const unread = String(item?.status || '') === 'unread';
              return (
                <div
                  key={item.inbox_id}
                  data-testid={`inbox-item-${item.inbox_id}`}
                  style={{
                    border: unread ? '1px solid #93c5fd' : '1px solid #e5e7eb',
                    borderRadius: '12px',
                    padding: '14px',
                    background: unread ? '#eff6ff' : '#ffffff',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: '12px',
                      flexWrap: 'wrap',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, color: '#111827' }}>
                        {item.title || item.event_type}
                      </div>
                    </div>
                    <div style={{ color: unread ? '#1d4ed8' : '#6b7280' }}>
                      {unread ? TEXT.unread : TEXT.read}
                    </div>
                  </div>
                  <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => handleOpen(item)}
                      style={primaryButtonStyle}
                    >
                      {TEXT.viewDetail}
                    </button>
                    {unread ? (
                      <button
                        type="button"
                        data-testid={`inbox-mark-read-${item.inbox_id}`}
                        onClick={() => handleMarkRead(item)}
                        disabled={busyId === item.inbox_id}
                        style={buttonStyle}
                      >
                        {busyId === item.inbox_id ? TEXT.processing : TEXT.markRead}
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
