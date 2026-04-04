import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import SignatureConfirmModal from '../features/operationApproval/components/SignatureConfirmModal';
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

const OPERATION_LABELS = {
  knowledge_file_upload: '文件上传',
  knowledge_file_delete: '文件删除',
  knowledge_base_create: '知识库新建',
  knowledge_base_delete: '知识库删除',
  legacy_document_review: '历史文档审核迁移',
};

const REQUEST_STATUS_LABELS = {
  in_approval: '审批中',
  approved_pending_execution: '待执行',
  executing: '执行中',
  executed: '已执行',
  rejected: '已驳回',
  withdrawn: '已撤回',
  execution_failed: '执行失败',
};

const REQUEST_STATUS_COLORS = {
  in_approval: '#2563eb',
  approved_pending_execution: '#d97706',
  executing: '#4f46e5',
  executed: '#15803d',
  rejected: '#dc2626',
  withdrawn: '#6b7280',
  execution_failed: '#b91c1c',
};

const STEP_STATUS_LABELS = {
  pending: '待处理',
  active: '审批中',
  approved: '已通过',
  rejected: '已驳回',
};

const STEP_STATUS_COLORS = {
  pending: '#9ca3af',
  active: '#2563eb',
  approved: '#15803d',
  rejected: '#dc2626',
};

const EVENT_LABELS = {
  request_submitted: '申请已提交',
  step_activated: '审批层已启动',
  step_member_auto_skipped: '审批成员自动跳过',
  step_auto_skipped: '审批层自动跳过',
  step_approved_by_user: '审批人已同意',
  request_approved: '审批已通过',
  request_rejected: '审批已驳回',
  request_withdrawn: '申请已撤回',
  execution_started: '开始执行',
  execution_completed: '执行完成',
  execution_failed: '执行失败',
  notification_inbox_created: '站内信已生成',
  notification_inbox_failed: '站内信生成失败',
  notification_external_enqueued: '外部通知已入队',
  notification_external_failed: '外部通知生成失败',
  notification_external_skipped: '未配置外部通知渠道',
};

const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'in_approval', label: '审批中' },
  { value: 'approved_pending_execution', label: '待执行' },
  { value: 'executing', label: '执行中' },
  { value: 'executed', label: '已执行' },
  { value: 'rejected', label: '已驳回' },
  { value: 'withdrawn', label: '已撤回' },
  { value: 'execution_failed', label: '执行失败' },
];

const APPROVAL_ERROR_MESSAGES = {
  training_record_missing: '当前审批账号缺少审批培训记录，请先补录培训记录后再审批或驳回。',
  training_curriculum_outdated: '当前审批账号的审批培训版本已过期，请完成最新版培训后再审批或驳回。',
  training_outcome_not_passed: '当前审批账号的审批培训未通过，无法审批或驳回。',
  training_effectiveness_not_met: '当前审批账号的审批培训有效性评估未通过，无法审批或驳回。',
  operator_certification_missing: '当前审批账号缺少审批上岗认证，请先补录认证后再审批或驳回。',
  operator_certification_outdated: '当前审批账号的审批上岗认证版本已过期，请更新认证后再审批或驳回。',
  operator_certification_expired: '当前审批账号的审批上岗认证已过期，请续签后再审批或驳回。',
  operator_certification_inactive: '当前审批账号的审批上岗认证当前无效，无法审批或驳回。',
  training_requirement_not_configured: '审批培训要求未配置完成，请先检查培训合规配置。',
};

const TRAINING_COMPLIANCE_ERROR_CODES = new Set([
  'training_record_missing',
  'training_curriculum_outdated',
  'training_outcome_not_passed',
  'training_effectiveness_not_met',
  'operator_certification_missing',
  'operator_certification_outdated',
  'operator_certification_expired',
  'operator_certification_inactive',
  'training_requirement_not_configured',
]);

function formatTime(value) {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return '-';
  return new Date(ms).toLocaleString();
}

function getOperationLabel(item) {
  const operationType = String(item?.operation_type || '').trim();
  return OPERATION_LABELS[operationType] || item?.operation_label || operationType || '-';
}

function getRequestStatusStyle(status) {
  return {
    color: REQUEST_STATUS_COLORS[String(status || '')] || '#374151',
    fontWeight: 700,
  };
}

function getStepStatusStyle(status) {
  return {
    color: STEP_STATUS_COLORS[String(status || '')] || '#374151',
    fontWeight: 600,
  };
}

function parseView(value) {
  return String(value || '').trim() === 'mine' ? 'mine' : 'todo';
}

function getActiveStep(detail) {
  return (detail?.steps || []).find((step) => String(step?.status || '') === 'active') || null;
}

function isCurrentPendingApprover(detail, userId) {
  if (String(detail?.status || '') !== 'in_approval') {
    return false;
  }
  const activeStep = getActiveStep(detail);
  if (!activeStep) return false;
  return (activeStep.approvers || []).some(
    (approver) => String(approver?.approver_user_id || '') === String(userId || '') && String(approver?.status || '') === 'pending'
  );
}

function canWithdraw(detail, user) {
  if (String(detail?.status || '') !== 'in_approval') return false;
  const currentUserId = String(user?.user_id || '');
  return String(detail?.applicant_user_id || '') === currentUserId || String(user?.role || '') === 'admin';
}

function buildSignaturePrompt(action, detail) {
  const approve = action === 'approve';
  const actionLabel = approve ? '通过' : '驳回';
  const requestId = detail?.request_id || '';
  const operationLabel = getOperationLabel(detail);
  return {
    title: '电子签名',
    description: `${actionLabel}申请单 ${requestId}（${operationLabel}）`,
    confirmLabel: approve ? '签名并通过' : '签名并驳回',
    defaultMeaning: approve ? '操作审批通过' : '操作审批驳回',
    defaultReason: approve ? '审批后同意执行该操作' : '审批后驳回该操作申请',
  };
}

function mapApprovalCenterErrorMessage(message) {
  const code = String(message || '').trim();
  if (!code) return '';
  return APPROVAL_ERROR_MESSAGES[code] || code;
}

function buildTrainingCompliancePath({ tab, userId, controlledAction = 'document_review' }) {
  const params = new URLSearchParams();
  if (tab) {
    params.set('tab', String(tab));
  }
  if (userId) {
    params.set('user_id', String(userId));
  }
  if (controlledAction) {
    params.set('controlled_action', String(controlledAction));
  }
  const query = params.toString();
  return query ? `/training-compliance?${query}` : '/training-compliance';
}

export default function ApprovalCenter() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState(() => parseView(searchParams.get('view')));
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get('status') || 'all');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [errorCode, setErrorCode] = useState('');
  const [selectedRequestId, setSelectedRequestId] = useState(() => searchParams.get('request_id') || '');
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState('');
  const selectedRequestIdRef = useRef(selectedRequestId);
  const {
    closeSignaturePrompt,
    promptSignature,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
  } = useSignaturePrompt();

  useEffect(() => {
    selectedRequestIdRef.current = selectedRequestId;
  }, [selectedRequestId]);

  const updateQuery = useCallback((nextView, nextStatus, nextRequestId) => {
    const params = new URLSearchParams();
    if (nextView && nextView !== 'todo') {
      params.set('view', nextView);
    }
    if (nextStatus && nextStatus !== 'all') {
      params.set('status', nextStatus);
    }
    if (nextRequestId) {
      params.set('request_id', nextRequestId);
    }
    setSearchParams(params);
  }, [setSearchParams]);

  const refreshList = useCallback(async (nextView = view, nextStatus = statusFilter) => {
    setLoading(true);
    setError('');
    setErrorCode('');
    try {
      const response = await operationApprovalApi.listRequests({
        view: nextView,
        status: nextStatus,
        limit: 100,
      });
      const nextItems = Array.isArray(response?.items) ? response.items : [];
      setItems(nextItems);
      const currentSelectedRequestId = String(selectedRequestIdRef.current || '');
      const stillExists = nextItems.some((item) => String(item?.request_id || '') === currentSelectedRequestId);
      const nextRequestId = stillExists
        ? currentSelectedRequestId
        : String(nextItems[0]?.request_id || '');
      setSelectedRequestId(nextRequestId);
      updateQuery(nextView, nextStatus, nextRequestId);
      if (!nextRequestId) {
        setDetail(null);
      }
    } catch (requestError) {
      setItems([]);
      setDetail(null);
      setSelectedRequestId('');
      const nextErrorCode = String(requestError?.message || '').trim();
      setErrorCode(nextErrorCode);
      setError(mapApprovalCenterErrorMessage(nextErrorCode || '加载审批申请失败'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, updateQuery, view]);

  const refreshDetail = useCallback(async (requestId) => {
    const nextRequestId = String(requestId || '');
    if (!nextRequestId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    setError('');
    setErrorCode('');
    try {
      const response = await operationApprovalApi.getRequest(nextRequestId);
      setDetail(response || null);
    } catch (requestError) {
      setDetail(null);
      const nextErrorCode = String(requestError?.message || '').trim();
      setErrorCode(nextErrorCode);
      setError(mapApprovalCenterErrorMessage(nextErrorCode || '加载审批详情失败'));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshList(view, statusFilter);
  }, [refreshList, statusFilter, view]);

  useEffect(() => {
    const nextView = parseView(searchParams.get('view'));
    if (nextView !== view) {
      setView(nextView);
    }
    const nextStatus = searchParams.get('status') || 'all';
    if (nextStatus !== statusFilter) {
      setStatusFilter(nextStatus);
    }
    const nextRequestId = searchParams.get('request_id') || '';
    if (nextRequestId !== selectedRequestId) {
      setSelectedRequestId(nextRequestId);
    }
  }, [searchParams, selectedRequestId, statusFilter, view]);

  useEffect(() => {
    refreshDetail(selectedRequestId);
  }, [refreshDetail, selectedRequestId]);

  const handleChangeView = useCallback((nextView) => {
    const cleanView = parseView(nextView);
    setView(cleanView);
    setSelectedRequestId('');
    updateQuery(cleanView, statusFilter, '');
  }, [statusFilter, updateQuery]);

  const handleChangeStatus = useCallback((nextStatus) => {
    const cleanStatus = String(nextStatus || 'all');
    setStatusFilter(cleanStatus);
    setSelectedRequestId('');
    updateQuery(view, cleanStatus, '');
  }, [updateQuery, view]);

  const handleSelectRequest = useCallback((requestId) => {
    const nextRequestId = String(requestId || '');
    setSelectedRequestId(nextRequestId);
    updateQuery(view, statusFilter, nextRequestId);
  }, [statusFilter, updateQuery, view]);

  const handleSignedAction = useCallback(async (action) => {
    if (!detail?.request_id) return;
    const signaturePayload = await promptSignature(buildSignaturePrompt(action, detail));
    if (!signaturePayload) return;
    setActionLoading(action);
    setError('');
    setErrorCode('');
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
      await refreshList(view, statusFilter);
      await refreshDetail(detail.request_id);
    } catch (requestError) {
      const nextErrorCode = String(requestError?.message || '').trim();
      setErrorCode(nextErrorCode);
      setError(
        mapApprovalCenterErrorMessage(
          nextErrorCode || `处理${action === 'approve' ? '通过' : '驳回'}失败`
        )
      );
    } finally {
      setActionLoading('');
    }
  }, [detail, promptSignature, refreshDetail, refreshList, statusFilter, view]);

  const handleWithdraw = useCallback(async () => {
    if (!detail?.request_id) return;
    const reason = window.prompt('请输入撤回原因（可留空）', '') ?? '';
    setActionLoading('withdraw');
    setError('');
    setErrorCode('');
    try {
      await operationApprovalApi.withdrawRequest(detail.request_id, {
        reason: String(reason || '').trim() || null,
      });
      await refreshList(view, statusFilter);
      await refreshDetail(detail.request_id);
    } catch (requestError) {
      const nextErrorCode = String(requestError?.message || '').trim();
      setErrorCode(nextErrorCode);
      setError(mapApprovalCenterErrorMessage(nextErrorCode || '撤回申请失败'));
    } finally {
      setActionLoading('');
    }
  }, [detail, refreshDetail, refreshList, statusFilter, view]);

  const currentPendingApprover = useMemo(
    () => isCurrentPendingApprover(detail, user?.user_id),
    [detail, user?.user_id]
  );
  const showTrainingHelp = TRAINING_COMPLIANCE_ERROR_CODES.has(String(errorCode || '').trim());
  const currentUserLabel = String(user?.full_name || '').trim()
    || String(user?.username || '').trim()
    || String(user?.user_id || '').trim()
    || '-';
  const trainingRecordPath = buildTrainingCompliancePath({
    tab: 'records',
    userId: user?.user_id,
  });
  const trainingCertificationPath = buildTrainingCompliancePath({
    tab: 'certifications',
    userId: user?.user_id,
  });

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
          <div style={{ color: '#4b5563', marginTop: '4px' }}>
            统一处理文件上传、文件删除、知识库新建和知识库删除申请。
          </div>
        </div>
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
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => refreshList(view, statusFilter)} style={buttonStyle}>刷新</button>
        </div>
      </div>

      {error ? (
        <div data-testid="approval-center-error" style={{ ...cardStyle, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b' }}>
          <div>{error}</div>
          {showTrainingHelp ? (
            <div style={{ marginTop: '10px', display: 'grid', gap: '10px' }}>
              <div data-testid="approval-center-training-help">
                当前审批账号：{currentUserLabel}。审批培训门禁已生效，需要先补录培训记录，再授予上岗认证。
              </div>
              {String(user?.role || '') === 'admin' ? (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <Link
                    data-testid="approval-center-training-record-link"
                    to={trainingRecordPath}
                    style={{ ...primaryButtonStyle, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
                  >
                    去补录培训记录
                  </Link>
                  <Link
                    data-testid="approval-center-training-certification-link"
                    to={trainingCertificationPath}
                    style={{ ...buttonStyle, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
                  >
                    去补录上岗认证
                  </Link>
                </div>
              ) : (
                <div>请联系管理员在“培训合规管理”中为当前账号补录培训记录并授予上岗认证。</div>
              )}
            </div>
          ) : null}
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 420px) minmax(0, 1fr)', gap: '16px' }}>
        <section style={cardStyle}>
          <div style={{ fontWeight: 700, marginBottom: '12px' }}>申请列表</div>
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
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'center' }}>
                      <strong>{getOperationLabel(item)}</strong>
                      <span data-testid={`approval-center-list-status-${item.request_id}`} style={getRequestStatusStyle(item.status)}>
                        {REQUEST_STATUS_LABELS[item.status] || item.status}
                      </span>
                    </div>
                    <div style={{ marginTop: '6px', color: '#111827' }}>{item.target_label || item.target_ref || '-'}</div>
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

        <section style={cardStyle}>
          {!selectedRequestId ? (
            <div style={{ color: '#6b7280' }}>请选择一条申请查看详情。</div>
          ) : detailLoading ? (
            <div>正在加载审批详情...</div>
          ) : !detail ? (
            <div style={{ color: '#6b7280' }}>未找到审批详情。</div>
          ) : (
            <div style={{ display: 'grid', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#111827' }}>{getOperationLabel(detail)}</div>
                  <div style={{ marginTop: '6px', color: '#4b5563' }}>申请单号：<code>{detail.request_id}</code></div>
                  <div style={{ marginTop: '4px', color: '#4b5563' }}>
                    当前状态：
                    {' '}
                    <span data-testid="approval-center-detail-status" style={getRequestStatusStyle(detail.status)}>
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
                  {canWithdraw(detail, user) ? (
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
                  <div>申请人：{detail.applicant_username || detail.applicant_user_id || '-'}</div>
                  <div>目标对象：{detail.target_label || detail.target_ref || '-'}</div>
                  <div>当前审批层：{detail.current_step_name || '-'}</div>
                  <div>提交时间：{formatTime(detail.submitted_at_ms)}</div>
                  <div>完成时间：{formatTime(detail.completed_at_ms)}</div>
                  <div>最后错误：{detail.last_error || '-'}</div>
                </div>

                <div style={{ ...cardStyle, padding: '14px' }}>
                  <div style={{ fontWeight: 700, marginBottom: '8px' }}>申请摘要</div>
                  {Object.entries(detail.summary || {}).length === 0 ? (
                    <div style={{ color: '#6b7280' }}>无摘要信息</div>
                  ) : (
                    <div style={{ display: 'grid', gap: '6px' }}>
                      {Object.entries(detail.summary || {}).map(([key, value]) => (
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
                        <strong>{`第 ${step.step_no} 层：${step.step_name}`}</strong>
                        <span style={getStepStatusStyle(step.status)}>{STEP_STATUS_LABELS[step.status] || step.status}</span>
                      </div>
                        <div style={{ marginTop: '8px', display: 'grid', gap: '6px' }}>
                          {(step.approvers || []).map((approver) => (
                            <div key={`${step.step_no}-${approver.approver_user_id}`} style={{ color: '#4b5563' }}>
                              {approver.approver_full_name || approver.approver_username || approver.approver_user_id}
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
                {(detail.events || []).length === 0 ? (
                  <div style={{ color: '#6b7280' }}>暂无时间线记录</div>
                ) : (
                  <div style={{ display: 'grid', gap: '10px' }}>
                    {(detail.events || []).map((event) => (
                      <div key={event.event_id} style={{ borderLeft: '3px solid #dbeafe', paddingLeft: '10px' }}>
                        <div style={{ fontWeight: 600 }}>{EVENT_LABELS[event.event_type] || event.event_type}</div>
                        <div style={{ color: '#4b5563', marginTop: '4px' }}>
                          操作人：{event.actor_username || event.actor_user_id || 'system'}
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
      </div>
    </div>
  );
}
