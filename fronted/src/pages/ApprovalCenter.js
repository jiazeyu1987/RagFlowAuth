import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SignatureConfirmModal } from '../features/review/components/SignatureConfirmModal';
import operationApprovalApi from '../features/operationApproval/api';
import { useSignaturePrompt } from '../features/operationApproval/useSignaturePrompt';
import { useAuth } from '../hooks/useAuth';

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

const dangerButtonStyle = {
  ...buttonStyle,
  background: '#dc2626',
  borderColor: '#dc2626',
  color: '#ffffff',
};

const statusLabelMap = {
  in_approval: '审批中',
  approved_pending_execution: '待执行',
  executing: '执行中',
  executed: '已执行',
  rejected: '已驳回',
  withdrawn: '已撤回',
  execution_failed: '执行失败',
};

const eventLabelMap = {
  request_submitted: '申请已提交',
  step_activated: '审批层已激活',
  step_approved_by_user: '审批人已同意',
  request_approved: '审批已通过',
  request_rejected: '审批已驳回',
  request_withdrawn: '申请已撤回',
  execution_started: '开始执行',
  execution_completed: '执行完成',
  execution_failed: '执行失败',
  notification_inbox_created: '已生成站内信',
  notification_external_enqueued: '已生成外部通知任务',
  notification_external_failed: '外部通知生成失败',
};

const formatTime = (value) => {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return '-';
  return new Date(ms).toLocaleString();
};

const formatObjectEntries = (value) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return [];
  return Object.entries(value).filter(([, item]) => item !== null && item !== undefined && item !== '');
};

const getActiveStep = (detail) => {
  const steps = Array.isArray(detail?.steps) ? detail.steps : [];
  return steps.find((item) => item?.status === 'active') || null;
};

const isCurrentPendingApprover = (detail, userId) => {
  const activeStep = getActiveStep(detail);
  if (!activeStep) return false;
  return (activeStep.approvers || []).some(
    (item) => String(item?.approver_user_id || '') === String(userId || '') && String(item?.status || '') === 'pending'
  );
};

const canWithdrawRequest = (detail, user) => {
  if (!detail || String(detail.status || '') !== 'in_approval') return false;
  const userId = String(user?.user_id || '');
  return String(detail.applicant_user_id || '') === userId || String(user?.role || '') === 'admin';
};

const buildSignaturePrompt = (action, detail) => {
  const isApprove = action === 'approve';
  const label = isApprove ? 'Approve' : 'Reject';
  return {
    title: 'Electronic Signature',
    description: `${label} request ${detail?.request_id || ''} (${detail?.operation_label || detail?.operation_type || ''})`,
    confirmLabel: isApprove ? 'Sign and approve' : 'Sign and reject',
    defaultMeaning: isApprove ? 'Operation approval' : 'Operation rejection',
    defaultReason: isApprove ? 'Approved after operation review' : 'Rejected during operation review',
  };
};

export default function ApprovalCenter() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState('todo');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState([]);
  const [selectedRequestId, setSelectedRequestId] = useState(() => searchParams.get('request_id') || '');
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState('');
  const {
    closeSignaturePrompt,
    promptSignature,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
  } = useSignaturePrompt();

  const refreshList = useCallback(async (nextView = view) => {
    setLoading(true);
    setError('');
    try {
      const response = await operationApprovalApi.listRequests({ view: nextView, limit: 100 });
      const nextItems = Array.isArray(response?.items) ? response.items : [];
      setItems(nextItems);
      if (!selectedRequestId && nextItems.length > 0) {
        const nextRequestId = String(nextItems[0].request_id || '');
        setSelectedRequestId(nextRequestId);
        const nextParams = new URLSearchParams(searchParams);
        nextParams.set('request_id', nextRequestId);
        setSearchParams(nextParams);
      }
    } catch (requestError) {
      setError(requestError?.message || 'Failed to load approval requests');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [searchParams, selectedRequestId, setSearchParams, view]);

  const refreshDetail = useCallback(async (requestId) => {
    const nextRequestId = String(requestId || '');
    if (!nextRequestId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    setError('');
    try {
      const response = await operationApprovalApi.getRequest(nextRequestId);
      setDetail(response || null);
    } catch (requestError) {
      setError(requestError?.message || 'Failed to load request detail');
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshList(view);
  }, [refreshList, view]);

  useEffect(() => {
    const requestIdFromQuery = searchParams.get('request_id') || '';
    if (requestIdFromQuery && requestIdFromQuery !== selectedRequestId) {
      setSelectedRequestId(requestIdFromQuery);
    }
  }, [searchParams, selectedRequestId]);

  useEffect(() => {
    refreshDetail(selectedRequestId);
  }, [refreshDetail, selectedRequestId]);

  const selectRequest = useCallback((requestId) => {
    const nextRequestId = String(requestId || '');
    setSelectedRequestId(nextRequestId);
    const nextParams = new URLSearchParams(searchParams);
    if (nextRequestId) {
      nextParams.set('request_id', nextRequestId);
    } else {
      nextParams.delete('request_id');
    }
    setSearchParams(nextParams);
  }, [searchParams, setSearchParams]);

  const currentPendingApprover = useMemo(
    () => isCurrentPendingApprover(detail, user?.user_id),
    [detail, user?.user_id]
  );

  const handleSignedAction = useCallback(async (action) => {
    if (!detail?.request_id) return;
    const signaturePayload = await promptSignature(buildSignaturePrompt(action, detail));
    if (!signaturePayload) return;

    setActionLoading(action);
    setError('');
    try {
      if (action === 'approve') {
        await operationApprovalApi.approveRequest(detail.request_id, {
          ...signaturePayload,
          notes: signaturePayload.signature_reason,
        });
      } else {
        await operationApprovalApi.rejectRequest(detail.request_id, {
          ...signaturePayload,
          notes: signaturePayload.signature_reason,
        });
      }
      await refreshList(view);
      await refreshDetail(detail.request_id);
    } catch (requestError) {
      setError(requestError?.message || `Failed to ${action} request`);
    } finally {
      setActionLoading('');
    }
  }, [detail, promptSignature, refreshDetail, refreshList, view]);

  const handleWithdraw = useCallback(async () => {
    if (!detail?.request_id) return;
    const reason = window.prompt('请输入撤回原因（可留空）', '') ?? '';
    setActionLoading('withdraw');
    setError('');
    try {
      await operationApprovalApi.withdrawRequest(detail.request_id, { reason: String(reason || '').trim() || null });
      await refreshList(view);
      await refreshDetail(detail.request_id);
    } catch (requestError) {
      setError(requestError?.message || 'Failed to withdraw request');
    } finally {
      setActionLoading('');
    }
  }, [detail, refreshDetail, refreshList, view]);

  const summaryEntries = formatObjectEntries(detail?.summary);
  const activeStep = getActiveStep(detail);

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="approval-center-page">
      <SignatureConfirmModal
        prompt={signaturePrompt}
        submitting={signatureSubmitting}
        error={signatureError}
        onClose={closeSignaturePrompt}
        onSubmit={submitSignaturePrompt}
      />

      <div style={{ ...cardStyle, display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>审批中心</div>
          <div style={{ color: '#4b5563', marginTop: '4px' }}>统一处理上传、删除、知识库新建、知识库删除申请。</div>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            data-testid="approval-center-tab-todo"
            onClick={() => setView('todo')}
            style={view === 'todo' ? primaryButtonStyle : buttonStyle}
          >
            待我审批
          </button>
          <button
            type="button"
            data-testid="approval-center-tab-mine"
            onClick={() => setView('mine')}
            style={view === 'mine' ? primaryButtonStyle : buttonStyle}
          >
            我发起的申请
          </button>
          <button type="button" onClick={() => refreshList(view)} style={buttonStyle}>
            刷新
          </button>
        </div>
      </div>

      {error ? (
        <div
          data-testid="approval-center-error"
          style={{ ...cardStyle, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b' }}
        >
          {error}
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 420px) minmax(0, 1fr)', gap: '16px' }}>
        <section style={cardStyle}>
          <div style={{ fontWeight: 700, marginBottom: '12px' }}>申请列表</div>
          {loading ? (
            <div>正在加载申请...</div>
          ) : items.length === 0 ? (
            <div style={{ color: '#6b7280' }}>当前没有申请。</div>
          ) : (
            <div style={{ display: 'grid', gap: '10px' }}>
              {items.map((item) => {
                const active = String(item?.request_id || '') === String(selectedRequestId || '');
                return (
                  <button
                    type="button"
                    key={item.request_id}
                    data-testid={`approval-center-item-${item.request_id}`}
                    onClick={() => selectRequest(item.request_id)}
                    style={{
                      textAlign: 'left',
                      border: active ? '1px solid #2563eb' : '1px solid #e5e7eb',
                      borderRadius: '12px',
                      padding: '12px',
                      background: active ? '#eff6ff' : '#ffffff',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'center' }}>
                      <strong>{item.operation_label || item.operation_type}</strong>
                      <span style={{ color: '#1d4ed8', fontSize: '0.85rem' }}>{statusLabelMap[item.status] || item.status}</span>
                    </div>
                    <div style={{ marginTop: '6px', color: '#111827' }}>{item.target_label || item.target_ref || '-'}</div>
                    <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.85rem' }}>
                      当前节点: {item.current_step_name || '-'}
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

        <section style={cardStyle}>
          {!selectedRequestId ? (
            <div style={{ color: '#6b7280' }}>请选择一个申请查看详情。</div>
          ) : detailLoading ? (
            <div>正在加载详情...</div>
          ) : !detail ? (
            <div style={{ color: '#6b7280' }}>未找到申请详情。</div>
          ) : (
            <div style={{ display: 'grid', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#111827' }}>
                    {detail.operation_label || detail.operation_type}
                  </div>
                  <div style={{ marginTop: '6px', color: '#4b5563' }}>
                    申请单号: <code>{detail.request_id}</code>
                  </div>
                  <div style={{ marginTop: '4px', color: '#4b5563' }}>
                    当前状态: {statusLabelMap[detail.status] || detail.status}
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
                  {canWithdrawRequest(detail, user) ? (
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

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' }}>
                <div style={{ ...cardStyle, padding: '14px' }}>
                  <div style={{ fontWeight: 700, marginBottom: '8px' }}>基本信息</div>
                  <div>申请人: {detail.applicant_username || detail.applicant_user_id || '-'}</div>
                  <div>目标对象: {detail.target_label || detail.target_ref || '-'}</div>
                  <div>当前审批层: {detail.current_step_name || '-'}</div>
                  <div>提交时间: {formatTime(detail.submitted_at_ms)}</div>
                  <div>完成时间: {formatTime(detail.completed_at_ms)}</div>
                  <div>最后错误: {detail.last_error || '-'}</div>
                </div>

                <div style={{ ...cardStyle, padding: '14px' }}>
                  <div style={{ fontWeight: 700, marginBottom: '8px' }}>申请摘要</div>
                  {summaryEntries.length === 0 ? (
                    <div style={{ color: '#6b7280' }}>无摘要信息</div>
                  ) : (
                    <div style={{ display: 'grid', gap: '6px' }}>
                      {summaryEntries.map(([key, value]) => (
                        <div key={key}>
                          <strong>{key}:</strong> {String(value)}
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
                        border: String(step.status || '') === 'active' ? '1px solid #2563eb' : '1px solid #e5e7eb',
                        borderRadius: '12px',
                        padding: '12px',
                        background: String(step.status || '') === 'active' ? '#eff6ff' : '#ffffff',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                        <strong>{`第 ${step.step_no} 层: ${step.step_name}`}</strong>
                        <span>{step.status}</span>
                      </div>
                      <div style={{ marginTop: '8px', display: 'grid', gap: '6px' }}>
                        {(step.approvers || []).map((approver) => (
                          <div key={`${step.step_no}-${approver.approver_user_id}`} style={{ color: '#4b5563' }}>
                            {approver.approver_username || approver.approver_user_id} - {approver.status}
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
                {(detail.events || []).length === 0 ? (
                  <div style={{ color: '#6b7280' }}>暂无时间线记录</div>
                ) : (
                  <div style={{ display: 'grid', gap: '10px' }}>
                    {(detail.events || []).map((event) => (
                      <div key={event.event_id} style={{ borderLeft: '3px solid #dbeafe', paddingLeft: '10px' }}>
                        <div style={{ fontWeight: 600 }}>{eventLabelMap[event.event_type] || event.event_type}</div>
                        <div style={{ color: '#4b5563', marginTop: '4px' }}>
                          操作人: {event.actor_username || event.actor_user_id || 'system'}
                          {event.step_no ? ` | 第 ${event.step_no} 层` : ''}
                          {activeStep && event.step_no === activeStep.step_no ? ' | 当前层' : ''}
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
      </div>
    </div>
  );
}
