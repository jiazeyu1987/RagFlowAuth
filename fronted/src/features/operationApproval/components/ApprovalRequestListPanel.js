import React from 'react';
import {
  REQUEST_STATUS_LABELS,
  STATUS_FILTER_OPTIONS,
  formatTime,
  getOperationLabel,
  getRequestStatusStyle,
} from '../approvalCenterConfig';
import { buttonStyle, cardStyle, primaryButtonStyle } from '../pageStyles';

export default function ApprovalRequestListPanel({
  view,
  statusFilter,
  items,
  loading,
  selectedRequestId,
  refreshList,
  handleChangeView,
  handleChangeStatus,
  handleSelectRequest,
}) {
  return (
    <section style={cardStyle}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
          marginBottom: '12px',
        }}
      >
        <div style={{ fontWeight: 700 }}>申请列表</div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            type="button"
            data-testid="approval-center-tab-todo"
            onClick={() => handleChangeView('todo')}
            style={view === 'todo' ? primaryButtonStyle : buttonStyle}
          >
            待我审批
          </button>
          <button
            type="button"
            data-testid="approval-center-tab-mine"
            onClick={() => handleChangeView('mine')}
            style={view === 'mine' ? primaryButtonStyle : buttonStyle}
          >
            我发起的申请
          </button>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#374151' }}>
            <span>状态</span>
            <select
              data-testid="approval-center-status-filter"
              value={statusFilter}
              onChange={(event) => handleChangeStatus(event.target.value)}
              style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
            >
              {STATUS_FILTER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => refreshList(view, statusFilter)} style={buttonStyle}>
            刷新
          </button>
        </div>
      </div>

      {loading ? (
        <div>正在加载申请...</div>
      ) : items.length === 0 ? (
        <div style={{ color: '#6b7280' }}>当前没有符合条件的申请。</div>
      ) : (
        <div style={{ display: 'grid', gap: '10px' }}>
          {items.map((item) => {
            const active = String(item?.request_id || '') === String(selectedRequestId || '');
            return (
              <button
                type="button"
                key={item.request_id}
                data-testid={`approval-center-item-${item.request_id}`}
                onClick={() => handleSelectRequest(item.request_id)}
                style={{
                  textAlign: 'left',
                  border: active ? '1px solid #2563eb' : '1px solid #e5e7eb',
                  borderRadius: '12px',
                  padding: '12px',
                  background: active ? '#eff6ff' : '#ffffff',
                  cursor: 'pointer',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: '8px',
                    alignItems: 'center',
                  }}
                >
                  <strong>{getOperationLabel(item)}</strong>
                  <span
                    data-testid={`approval-center-list-status-${item.request_id}`}
                    style={getRequestStatusStyle(item.status)}
                  >
                    {REQUEST_STATUS_LABELS[item.status] || item.status}
                  </span>
                </div>
                <div style={{ marginTop: '6px', color: '#111827' }}>
                  {item.target_label || item.target_ref || '-'}
                </div>
                <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.85rem' }}>
                  当前审批层：{item.current_step_name || '-'}
                </div>
                <div style={{ marginTop: '4px', color: '#9ca3af', fontSize: '0.8rem' }}>
                  {formatTime(item.submitted_at_ms)}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
