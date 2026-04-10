import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import { DOCUMENT_SOURCE } from '../../shared/documents/constants';

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

export const TRAINING_COMPLIANCE_ERROR_CODES = new Set([
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

export const parseView = (value) => (String(value || '').trim() === 'mine' ? 'mine' : 'todo');

export const getActiveStep = (detail) =>
  (detail?.steps || []).find((step) => String(step?.status || '') === 'active') || null;

export const isCurrentPendingApprover = (detail, userId) => {
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

export const canWithdraw = (detail, user) => {
  if (String(detail?.status || '') !== 'in_approval') return false;
  const currentUserId = String(user?.user_id || '');
  return (
    String(detail?.applicant_user_id || '') === currentUserId ||
    String(user?.role || '') === 'admin'
  );
};

export const buildSignaturePrompt = (action, detail, getOperationLabel) => {
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

export const mapApprovalCenterErrorMessage = (message) => {
  const code = String(message || '').trim();
  if (!code) return '';
  return APPROVAL_ERROR_MESSAGES[code] || mapUserFacingErrorMessage(code, '审批处理失败，请稍后重试');
};

export const buildTrainingCompliancePath = ({
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

export const getVisibleSummaryEntries = (summary) =>
  Object.entries(summary || {}).filter(([key]) => {
    const normalizedKey = String(key || '').trim().toLowerCase();
    return !HIDDEN_SUMMARY_FIELDS.has(normalizedKey);
  });

export const getVisibleEvents = (events) =>
  (events || []).filter((event) => {
    const eventType = String(event?.event_type || '').trim();
    return !HIDDEN_EVENT_TYPES.has(eventType);
  });

export const getApprovalSummaryPreviewTarget = (detail, key) => {
  if (String(key || '').trim().toLowerCase() !== 'filename') {
    return null;
  }
  if (String(detail?.operation_type || '').trim() !== 'knowledge_file_upload') {
    return null;
  }

  const artifact = (detail?.artifacts || []).find(
    (item) =>
      String(item?.artifact_type || '').trim() === 'knowledge_file_upload' &&
      String(item?.artifact_id || '').trim()
  );
  if (!artifact) {
    return null;
  }

  return {
    source: DOCUMENT_SOURCE.OPERATION_APPROVAL_ARTIFACT,
    docId: String(artifact.artifact_id),
    requestId: String(detail?.request_id || ''),
    filename: String(
      artifact.file_name || detail?.summary?.filename || detail?.target_label || 'approval_artifact'
    ),
    title: String(
      artifact.file_name || detail?.summary?.filename || detail?.target_label || 'approval_artifact'
    ),
  };
};
