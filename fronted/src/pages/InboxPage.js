import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import operationApprovalApi from '../features/operationApproval/api';
import { publishInboxUnreadCount } from '../features/notification/inboxUnreadSync';

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

const formatTime = (value) => {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return '-';
  return new Date(ms).toLocaleString();
};

const resolveApprovalLink = (item) => {
  if (item?.link_path) return item.link_path;
  const requestId = String(item?.payload?.request_id || '').trim();
  return requestId ? `/approvals?request_id=${encodeURIComponent(requestId)}` : '/approvals';
};

export default function InboxPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [busyId, setBusyId] = useState('');
  const [markAllBusy, setMarkAllBusy] = useState(false);
  const unreadCountRef = useRef(0);

  useEffect(() => {
    unreadCountRef.current = Number(unreadCount || 0);
  }, [unreadCount]);

  const syncUnreadCount = useCallback((valueOrUpdater) => {
    const base = Number(unreadCountRef.current || 0);
    const rawValue = typeof valueOrUpdater === 'function' ? valueOrUpdater(base) : valueOrUpdater;
    const normalized = Number.isFinite(Number(rawValue)) && Number(rawValue) > 0 ? Number(rawValue) : 0;
    unreadCountRef.current = normalized;
    setUnreadCount(normalized);
    publishInboxUnreadCount(normalized);
    return normalized;
  }, []);

  const loadData = useCallback(async (nextUnreadOnly = unreadOnly) => {
    setLoading(true);
    setError('');
    try {
      const response = await operationApprovalApi.listInbox({ unreadOnly: nextUnreadOnly, limit: 100 });
      setItems(Array.isArray(response?.items) ? response.items : []);
      syncUnreadCount(Number(response?.unread_count || 0));
    } catch (requestError) {
      setError(requestError?.message || 'Failed to load inbox');
      setItems([]);
      syncUnreadCount(0);
    } finally {
      setLoading(false);
    }
  }, [syncUnreadCount, unreadOnly]);

  useEffect(() => {
    loadData(unreadOnly);
  }, [loadData, unreadOnly]);

  const handleMarkRead = useCallback(async (item) => {
    const inboxId = String(item?.inbox_id || '');
    if (!inboxId) return;
    setBusyId(inboxId);
    setError('');
    try {
      await operationApprovalApi.markInboxRead(inboxId);
      if (String(item?.status || '') === 'unread') {
        setItems((prev) => {
          if (unreadOnly) {
            return prev.filter((entry) => String(entry?.inbox_id || '') !== inboxId);
          }
          return prev.map((entry) => (
            String(entry?.inbox_id || '') === inboxId
              ? { ...entry, status: 'read' }
              : entry
          ));
        });
        syncUnreadCount((prev) => Math.max(0, Number(prev || 0) - 1));
      }
    } catch (requestError) {
      setError(requestError?.message || 'Failed to update inbox item');
    } finally {
      setBusyId('');
    }
  }, [syncUnreadCount, unreadOnly]);

  const handleOpen = useCallback(async (item) => {
    if (String(item?.status || '') === 'unread') {
      await handleMarkRead(item);
    }
    navigate(resolveApprovalLink(item));
  }, [handleMarkRead, navigate]);

  const handleMarkAllRead = useCallback(async () => {
    setMarkAllBusy(true);
    setError('');
    try {
      await operationApprovalApi.markAllInboxRead();
      setItems((prev) => (
        unreadOnly
          ? []
          : prev.map((entry) => ({ ...entry, status: 'read' }))
      ));
      syncUnreadCount(0);
    } catch (requestError) {
      setError(requestError?.message || 'Failed to mark all inbox items as read');
    } finally {
      setMarkAllBusy(false);
    }
  }, [syncUnreadCount, unreadOnly]);

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="inbox-page">
      <div style={{ ...cardStyle, display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>站内信</div>
          <div style={{ color: '#4b5563', marginTop: '4px' }}>审批流通知会统一进入这里，并可跳转到申请详情。</div>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span data-testid="inbox-unread-count">{`未读 ${unreadCount}`}</span>
          <button
            type="button"
            data-testid="inbox-toggle-unread"
            onClick={() => setUnreadOnly((prev) => !prev)}
            style={buttonStyle}
          >
            {unreadOnly ? '查看全部' : '仅看未读'}
          </button>
          <button
            type="button"
            data-testid="inbox-mark-all-read"
            onClick={handleMarkAllRead}
            disabled={markAllBusy || unreadCount <= 0}
            style={primaryButtonStyle}
          >
            {markAllBusy ? '处理中...' : '全部标记已读'}
          </button>
        </div>
      </div>

      {error ? (
        <div data-testid="inbox-error" style={{ ...cardStyle, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b' }}>
          {error}
        </div>
      ) : null}

      <div style={cardStyle}>
        {loading ? (
          <div>正在加载站内信...</div>
        ) : items.length === 0 ? (
          <div style={{ color: '#6b7280' }}>当前没有站内信。</div>
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontWeight: 700, color: '#111827' }}>{item.title || item.event_type}</div>
                      <div style={{ color: '#4b5563', marginTop: '6px', whiteSpace: 'pre-wrap' }}>{item.body || '-'}</div>
                    </div>
                    <div style={{ color: unread ? '#1d4ed8' : '#6b7280' }}>{unread ? '未读' : '已读'}</div>
                  </div>
                  <div style={{ marginTop: '10px', color: '#6b7280', fontSize: '0.9rem' }}>
                    事件类型: {item.event_type || '-'} | 时间: {formatTime(item.created_at_ms)}
                  </div>
                  <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button type="button" onClick={() => handleOpen(item)} style={primaryButtonStyle}>
                      查看详情
                    </button>
                    {unread ? (
                      <button
                        type="button"
                        data-testid={`inbox-mark-read-${item.inbox_id}`}
                        onClick={() => handleMarkRead(item)}
                        disabled={busyId === item.inbox_id}
                        style={buttonStyle}
                      >
                        {busyId === item.inbox_id ? '处理中...' : '标记已读'}
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
