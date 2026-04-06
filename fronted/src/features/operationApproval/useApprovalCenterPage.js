import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import operationApprovalApi from './api';
import { useSignaturePrompt } from './useSignaturePrompt';
import { useAuth } from '../../hooks/useAuth';
import { getDisplayName } from '../../shared/users/displayName';

const APPROVAL_ERROR_MESSAGES = {
  training_record_missing:
    '当前审批账号缺少审批培训记录，请先补录培训记录后再审批或驳回。',
  training_curriculum_outdated:
    '当前审批账号的审批培训版本已过期，请完成最新版培训后再审批或驳回。',
  training_outcome_not_passed:
    '当前审批账号的审批培训未通过，无法审批或驳回。',
  training_effectiveness_not_met:
    '当前审批账号的审批培训有效性评估未通过，无法审批或驳回。',
  operator_certification_missing:
    '当前审批账号缺少审批上岗认证，请先补录认证后再审批或驳回。',
  operator_certification_outdated:
    '当前审批账号的审批上岗认证版本已过期，请更新认证后再审批或驳回。',
  operator_certification_expired:
    '当前审批账号的审批上岗认证已过期，请续签后再审批或驳回。',
  operator_certification_inactive:
    '当前审批账号的审批上岗认证当前无效，无法审批或驳回。',
  training_requirement_not_configured:
    '审批培训要求未配置完成，请先检查培训合规配置。',
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

const HIDDEN_SUMMARY_FIELDS = new Set(['kb_id', 'kb_name', 'kb_ref', 'mime_type']);
const HIDDEN_EVENT_TYPES = new Set([
  'notification_inbox_created',
  'notification_external_skipped',
]);

const parseView = (value) => (String(value || '').trim() === 'mine' ? 'mine' : 'todo');

const getActiveStep = (detail) =>
  (detail?.steps || []).find((step) => String(step?.status || '') === 'active') || null;

const isCurrentPendingApprover = (detail, userId) => {
  if (String(detail?.status || '') !== 'in_approval') {
    return false;
  }
  const activeStep = getActiveStep(detail);
  if (!activeStep) return false;
  return (activeStep.approvers || []).some(
    (approver) =>
      String(approver?.approver_user_id || '') === String(userId || '') &&
      String(approver?.status || '') === 'pending'
  );
};

const canWithdraw = (detail, user) => {
  if (String(detail?.status || '') !== 'in_approval') return false;
  const currentUserId = String(user?.user_id || '');
  return (
    String(detail?.applicant_user_id || '') === currentUserId ||
    String(user?.role || '') === 'admin'
  );
};

const buildSignaturePrompt = (action, detail, getOperationLabel) => {
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
};

const mapApprovalCenterErrorMessage = (message) => {
  const code = String(message || '').trim();
  if (!code) return '';
  return APPROVAL_ERROR_MESSAGES[code] || code;
};

const buildTrainingCompliancePath = ({
  tab,
  userId,
  controlledAction = 'document_review',
}) => {
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
};

const getVisibleSummaryEntries = (summary) =>
  Object.entries(summary || {}).filter(([key]) => {
    const normalizedKey = String(key || '').trim().toLowerCase();
    return !HIDDEN_SUMMARY_FIELDS.has(normalizedKey);
  });

const getVisibleEvents = (events) =>
  (events || []).filter((event) => {
    const eventType = String(event?.event_type || '').trim();
    return !HIDDEN_EVENT_TYPES.has(eventType);
  });

export default function useApprovalCenterPage({ getOperationLabel }) {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState(() => parseView(searchParams.get('view')));
  const [statusFilter, setStatusFilter] = useState(
    () => searchParams.get('status') || 'all'
  );
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [errorCode, setErrorCode] = useState('');
  const [selectedRequestId, setSelectedRequestId] = useState(
    () => searchParams.get('request_id') || ''
  );
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

  const updateQuery = useCallback(
    (nextView, nextStatus, nextRequestId) => {
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
    },
    [setSearchParams]
  );

  const refreshList = useCallback(
    async (nextView = view, nextStatus = statusFilter) => {
      setLoading(true);
      setError('');
      setErrorCode('');
      try {
        const nextItems = await operationApprovalApi.listRequests({
          view: nextView,
          status: nextStatus,
          limit: 100,
        });
        setItems(nextItems);

        const currentSelectedRequestId = String(selectedRequestIdRef.current || '');
        const stillExists = nextItems.some(
          (item) => String(item?.request_id || '') === currentSelectedRequestId
        );
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
        setError(
          mapApprovalCenterErrorMessage(nextErrorCode || '加载审批申请失败')
        );
      } finally {
        setLoading(false);
      }
    },
    [statusFilter, updateQuery, view]
  );

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
      setDetail(await operationApprovalApi.getRequest(nextRequestId));
    } catch (requestError) {
      setDetail(null);
      const nextErrorCode = String(requestError?.message || '').trim();
      setErrorCode(nextErrorCode);
      setError(
        mapApprovalCenterErrorMessage(nextErrorCode || '加载审批详情失败')
      );
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

  const handleChangeView = useCallback(
    (nextView) => {
      const cleanView = parseView(nextView);
      setView(cleanView);
      setSelectedRequestId('');
      updateQuery(cleanView, statusFilter, '');
    },
    [statusFilter, updateQuery]
  );

  const handleChangeStatus = useCallback(
    (nextStatus) => {
      const cleanStatus = String(nextStatus || 'all');
      setStatusFilter(cleanStatus);
      setSelectedRequestId('');
      updateQuery(view, cleanStatus, '');
    },
    [updateQuery, view]
  );

  const handleSelectRequest = useCallback(
    (requestId) => {
      const nextRequestId = String(requestId || '');
      setSelectedRequestId(nextRequestId);
      updateQuery(view, statusFilter, nextRequestId);
    },
    [statusFilter, updateQuery, view]
  );

  const handleSignedAction = useCallback(
    async (action) => {
      if (!detail?.request_id) return;
      const signaturePayload = await promptSignature(
        buildSignaturePrompt(action, detail, getOperationLabel)
      );
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
    },
    [detail, getOperationLabel, promptSignature, refreshDetail, refreshList, statusFilter, view]
  );

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
      setError(
        mapApprovalCenterErrorMessage(nextErrorCode || '撤回申请失败')
      );
    } finally {
      setActionLoading('');
    }
  }, [detail, refreshDetail, refreshList, statusFilter, view]);

  const currentPendingApprover = useMemo(
    () => isCurrentPendingApprover(detail, user?.user_id),
    [detail, user?.user_id]
  );

  const withdrawable = useMemo(() => canWithdraw(detail, user), [detail, user]);
  const visibleSummaryEntries = useMemo(
    () => getVisibleSummaryEntries(detail?.summary),
    [detail?.summary]
  );
  const visibleEvents = useMemo(
    () => getVisibleEvents(detail?.events),
    [detail?.events]
  );
  const showTrainingHelp = TRAINING_COMPLIANCE_ERROR_CODES.has(
    String(errorCode || '').trim()
  );
  const currentUserLabel = getDisplayName(user);
  const trainingRecordPath = buildTrainingCompliancePath({
    tab: 'records',
    userId: user?.user_id,
  });
  const trainingCertificationPath = buildTrainingCompliancePath({
    tab: 'certifications',
    userId: user?.user_id,
  });

  return {
    user,
    view,
    statusFilter,
    items,
    loading,
    error,
    errorCode,
    selectedRequestId,
    detail,
    detailLoading,
    actionLoading,
    currentPendingApprover,
    withdrawable,
    visibleSummaryEntries,
    visibleEvents,
    showTrainingHelp,
    currentUserLabel,
    trainingRecordPath,
    trainingCertificationPath,
    closeSignaturePrompt,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
    refreshList,
    handleChangeView,
    handleChangeStatus,
    handleSelectRequest,
    handleSignedAction,
    handleWithdraw,
  };
}
