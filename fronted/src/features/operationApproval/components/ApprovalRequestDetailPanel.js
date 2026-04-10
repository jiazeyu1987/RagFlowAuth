import React from 'react';
import {
  EVENT_LABELS,
  REQUEST_STATUS_LABELS,
  STEP_STATUS_LABELS,
  formatTime,
  getOperationLabel,
  getRequestStatusStyle,
  getStepStatusStyle,
} from '../approvalCenterConfig';
import { buttonStyle, cardStyle, dangerButtonStyle, primaryButtonStyle } from '../pageStyles';

export default function ApprovalRequestDetailPanel({
  selectedRequestId,
  detail,
  detailLoading,
  actionLoading,
  currentPendingApprover,
  withdrawable,
  visibleSummaryEntries,
  previewableSummaryKeys,
  visibleEvents,
  handlePreviewSummaryEntry,
  handleSignedAction,
  handleWithdraw,
}) {
  return (
    <section style={cardStyle}>
      {!selectedRequestId ? (
        <div style={{ color: '#6b7280' }}>请选择一条申请查看详情。</div>
      ) : detailLoading ? (
        <div>正在加载审批详情...</div>
      ) : !detail ? (
        <div style={{ color: '#6b7280' }}>未找到审批详情。</div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: '12px',
              alignItems: 'flex-start',
              flexWrap: 'wrap',
            }}
          >
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#111827' }}>
                {getOperationLabel(detail)}
              </div>
              <div style={{ marginTop: '4px', color: '#4b5563' }}>
                当前状态：
                {' '}
                <span
                  data-testid="approval-center-detail-status"
                  style={getRequestStatusStyle(detail.status)}
                >
                  {REQUEST_STATUS_LABELS[detail.status] || detail.status}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {currentPendingApprover ? (
                <>
                  <button
                    type="button"
                    data-testid="approval-center-approve"
                    onClick={() => handleSignedAction('approve')}
                    disabled={actionLoading === 'approve'}
                    style={primaryButtonStyle}
                  >
                    {actionLoading === 'approve' ? '处理中...' : '审批通过'}
                  </button>
                  <button
                    type="button"
                    data-testid="approval-center-reject"
                    onClick={() => handleSignedAction('reject')}
                    disabled={actionLoading === 'reject'}
                    style={dangerButtonStyle}
                  >
                    {actionLoading === 'reject' ? '处理中...' : '驳回'}
                  </button>
                </>
              ) : null}

              {withdrawable ? (
                <button
                  type="button"
                  data-testid="approval-center-withdraw"
                  onClick={handleWithdraw}
                  disabled={actionLoading === 'withdraw'}
                  style={buttonStyle}
                >
                  {actionLoading === 'withdraw' ? '处理中...' : '撤回申请'}
                </button>
              ) : null}
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
              gap: '12px',
            }}
          >
            <div style={{ ...cardStyle, padding: '14px' }}>
              <div style={{ fontWeight: 700, marginBottom: '8px' }}>基本信息</div>
              <div>
                申请人：
                {detail.applicant_full_name || detail.applicant_username || detail.applicant_user_id || '-'}
              </div>
              <div>目标对象：{detail.target_label || detail.target_ref || '-'}</div>
              <div>当前审批层：{detail.current_step_name || '-'}</div>
              <div>提交时间：{formatTime(detail.submitted_at_ms)}</div>
              <div>完成时间：{formatTime(detail.completed_at_ms)}</div>
              <div>最后错误：{detail.last_error || '-'}</div>
            </div>

            <div style={{ ...cardStyle, padding: '14px' }}>
              <div style={{ fontWeight: 700, marginBottom: '8px' }}>申请摘要</div>
              {visibleSummaryEntries.length === 0 ? (
                <div style={{ color: '#6b7280' }}>无摘要信息</div>
              ) : (
                <div style={{ display: 'grid', gap: '6px' }}>
                  {visibleSummaryEntries.map(([key, value]) => (
                    <div key={key}>
                      <strong>{key}:</strong>{' '}
                      {previewableSummaryKeys?.has(String(key)) ? (
                        <button
                          type="button"
                          data-testid={`approval-summary-preview-${String(key)}`}
                          onClick={() => handlePreviewSummaryEntry(String(key))}
                          style={{
                            border: 'none',
                            background: 'transparent',
                            padding: 0,
                            color: '#2563eb',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                            font: 'inherit',
                          }}
                        >
                          {String(value)}
                        </button>
                      ) : (
                        String(value)
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div style={{ ...cardStyle, padding: '14px' }}>
            <div style={{ fontWeight: 700, marginBottom: '10px' }}>审批步骤</div>
            <div style={{ display: 'grid', gap: '10px' }}>
              {(detail.steps || []).map((step) => (
                <div
                  key={step.request_step_id || `${detail.request_id}-${step.step_no}`}
                  style={{
                    border:
                      String(step.status || '') === 'active'
                        ? '1px solid #2563eb'
                        : '1px solid #e5e7eb',
                    borderRadius: '12px',
                    padding: '12px',
                    background:
                      String(step.status || '') === 'active'
                        ? '#eff6ff'
                        : '#ffffff',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: '8px',
                      flexWrap: 'wrap',
                    }}
                  >
                    <strong>{`第 ${step.step_no} 层：${step.step_name}`}</strong>
                    <span style={getStepStatusStyle(step.status)}>
                      {STEP_STATUS_LABELS[step.status] || step.status}
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', display: 'grid', gap: '6px' }}>
                    {(step.approvers || []).map((approver) => (
                      <div
                        key={`${step.step_no}-${approver.approver_user_id}`}
                        style={{ color: '#4b5563' }}
                      >
                        {approver.approver_full_name ||
                          approver.approver_username ||
                          approver.approver_user_id ||
                          '-'}
                        {' - '}
                        <span style={getStepStatusStyle(approver.status)}>
                          {STEP_STATUS_LABELS[approver.status] || approver.status}
                        </span>
                        {approver.acted_at_ms ? ` (${formatTime(approver.acted_at_ms)})` : ''}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...cardStyle, padding: '14px' }}>
            <div style={{ fontWeight: 700, marginBottom: '10px' }}>时间线</div>
            {visibleEvents.length === 0 ? (
              <div style={{ color: '#6b7280' }}>暂无时间线记录</div>
            ) : (
              <div style={{ display: 'grid', gap: '10px' }}>
                {visibleEvents.map((event) => (
                  <div
                    key={event.event_id}
                    style={{ borderLeft: '3px solid #dbeafe', paddingLeft: '10px' }}
                  >
                    <div style={{ fontWeight: 600 }}>
                      {EVENT_LABELS[event.event_type] || event.event_type}
                    </div>
                    <div style={{ color: '#4b5563', marginTop: '4px' }}>
                      操作人：
                      {event.actor_full_name || event.actor_username || event.actor_user_id || 'system'}
                      {event.step_no ? ` | 第 ${event.step_no} 层` : ''}
                    </div>
                    <div style={{ color: '#9ca3af', marginTop: '4px', fontSize: '0.85rem' }}>
                      {formatTime(event.created_at_ms)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
