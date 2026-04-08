export const OPERATION_LABELS = {
  knowledge_file_upload: '文件上传',
  knowledge_file_delete: '文件删除',
  knowledge_base_create: '知识库新建',
  knowledge_base_delete: '知识库删除',
  legacy_document_review: '历史文档审核迁移',
};

export const REQUEST_STATUS_LABELS = {
  in_approval: '审批中',
  approved_pending_execution: '待执行',
  executing: '执行中',
  executed: '已执行',
  rejected: '已驳回',
  withdrawn: '已撤回',
  execution_failed: '执行失败',
};

export const REQUEST_STATUS_COLORS = {
  in_approval: '#2563eb',
  approved_pending_execution: '#d97706',
  executing: '#4f46e5',
  executed: '#15803d',
  rejected: '#dc2626',
  withdrawn: '#6b7280',
  execution_failed: '#b91c1c',
};

export const STEP_STATUS_LABELS = {
  pending: '待处理',
  active: '审批中',
  approved: '已通过',
  rejected: '已驳回',
};

export const STEP_STATUS_COLORS = {
  pending: '#9ca3af',
  active: '#2563eb',
  approved: '#15803d',
  rejected: '#dc2626',
};

export const EVENT_LABELS = {
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

export const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'in_approval', label: '审批中' },
  { value: 'approved_pending_execution', label: '待执行' },
  { value: 'executing', label: '执行中' },
  { value: 'executed', label: '已执行' },
  { value: 'rejected', label: '已驳回' },
  { value: 'withdrawn', label: '已撤回' },
  { value: 'execution_failed', label: '执行失败' },
];

export function formatTime(value) {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return '-';
  return new Date(ms).toLocaleString();
}

export function getOperationLabel(item) {
  const operationType = String(item?.operation_type || '').trim();
  return OPERATION_LABELS[operationType] || item?.operation_label || operationType || '-';
}

export function getRequestStatusStyle(status) {
  return {
    color: REQUEST_STATUS_COLORS[String(status || '')] || '#374151',
    fontWeight: 700,
  };
}

export function getStepStatusStyle(status) {
  return {
    color: STEP_STATUS_COLORS[String(status || '')] || '#374151',
    fontWeight: 600,
  };
}
