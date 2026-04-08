export const cardStyle = {
  background: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '16px',
  marginTop: '16px',
};

export const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

export const cellStyle = {
  borderBottom: '1px solid #e5e7eb',
  textAlign: 'left',
  padding: '8px',
  verticalAlign: 'top',
  fontSize: '0.9rem',
};

export const inputStyle = {
  padding: '8px 10px',
  borderRadius: '8px',
  border: '1px solid #d1d5db',
  width: '100%',
};

export const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  background: 'white',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

export const primaryButtonStyle = {
  ...buttonStyle,
  border: 'none',
  background: '#2563eb',
  color: 'white',
};

export const tabButtonStyle = {
  ...buttonStyle,
  padding: '10px 16px',
};

export const TEXT = {
  title: '电子签名',
  loading: '正在加载电子签名数据...',
  search: '查询',
  reset: '重置',
  total: '总数',
  noData: '暂无电子签名记录',
  filters: '筛选条件',
  signatureId: '签名 ID',
  recordType: '记录类型',
  recordId: '记录 ID',
  action: '操作',
  fullName: '姓名',
  signer: '签署人',
  status: '状态',
  signedAt: '签署时间',
  meaning: '签名含义',
  reason: '签署原因',
  verified: '验签结果',
  view: '查看',
  verify: '验签',
  detail: '签名详情',
  recordHash: '记录哈希',
  signatureHash: '签名哈希',
  signTokenId: '挑战 ID',
  yes: '通过',
  no: '未通过',
  notSelected: '请先选择一条签名记录',
  authorizationTitle: '签名授权管理',
  authorizationStatus: '授权状态',
  authorizationEnabled: '已授权',
  authorizationDisabled: '未授权',
  authorizationAction: '授权操作',
  enable: '启用',
  disable: '停用',
  signatureTab: '电子签名',
  authorizationTab: '签名授权管理',
};

const RECORD_TYPE_LABELS = {
  operation_approval_request: '操作审批',
  knowledge_document_review: '文档审核',
};

const ACTION_LABELS = {
  operation_approval_approve: '审批通过',
  operation_approval_reject: '审批驳回',
  document_approve: '文档批准',
  document_reject: '文档驳回',
};

const STATUS_LABELS = {
  signed: '已签署',
};

export const getRecordTypeLabel = (value) =>
  RECORD_TYPE_LABELS[String(value || '')] || String(value || '-');

export const getActionLabel = (value) =>
  ACTION_LABELS[String(value || '')] || String(value || '-');

export const getStatusLabel = (value) =>
  STATUS_LABELS[String(value || '')] || String(value || '-');

export const getSignerFullName = (item) => item?.signed_by_full_name || '-';

export const getSignerLabel = (item) => item?.signed_by_username || item?.signed_by || '-';

export const RECORD_TYPE_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'operation_approval_request', label: getRecordTypeLabel('operation_approval_request') },
  { value: 'knowledge_document_review', label: getRecordTypeLabel('knowledge_document_review') },
];

export const ACTION_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'operation_approval_approve', label: getActionLabel('operation_approval_approve') },
  { value: 'operation_approval_reject', label: getActionLabel('operation_approval_reject') },
  { value: 'document_approve', label: getActionLabel('document_approve') },
  { value: 'document_reject', label: getActionLabel('document_reject') },
];

export const formatTime = (ms) => {
  if (!ms) return '-';
  const value = Number(ms);
  if (!Number.isFinite(value) || value <= 0) return '-';
  return new Date(value).toLocaleString();
};

export const getAuthorizationButtonTestId = (userId) =>
  `electronic-signature-authorization-toggle-${String(userId || '').replace(/[^a-zA-Z0-9_-]/g, '_')}`;
