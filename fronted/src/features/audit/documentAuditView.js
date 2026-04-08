export const MOBILE_BREAKPOINT = 768;

export const STATUS_LABELS = {
  pending: '\u5f85\u5ba1\u6838',
  approved: '\u5df2\u901a\u8fc7',
  rejected: '\u5df2\u9a73\u56de',
};

export const STATUS_STYLES = {
  pending: { backgroundColor: '#f59e0b' },
  approved: { backgroundColor: '#10b981' },
  rejected: { backgroundColor: '#ef4444' },
};

export const EFFECTIVE_STATUS_LABELS = {
  approved: '\u5f53\u524d\u751f\u6548',
  pending: '\u5f85\u5ba1\u7248\u672c',
  rejected: '\u5df2\u9a73\u56de',
  superseded: '\u5386\u53f2\u7248\u672c',
  archived: '\u5f52\u6863\u7248\u672c',
};

export const VERIFIED_TEXT = {
  yes: '\u901a\u8fc7',
  no: '\u5931\u8d25',
  unknown: '-',
};

export const BASE_HEADER_CELL_STYLE = {
  padding: '12px 16px',
  textAlign: 'left',
  borderBottom: '1px solid #e5e7eb',
  fontSize: '0.85rem',
  fontWeight: '600',
};

export const MANIFEST_LABEL_STYLE = {
  color: '#6b7280',
  fontSize: '0.8rem',
};

export const MANIFEST_VALUE_STYLE = {
  color: '#111827',
  fontSize: '0.85rem',
  wordBreak: 'break-word',
};

export const OTHER_USER_TEXT = '\u5176\u4ed6';

export const getCountLabel = (count) => `\u5171 ${count} \u6761\u8bb0\u5f55`;

export const getDocumentsEmptyText = (hasFilters) =>
  hasFilters ? '\u6ca1\u6709\u7b26\u5408\u6761\u4ef6\u7684\u8bb0\u5f55' : '\u6682\u65e0\u5ba1\u6838\u8bb0\u5f55';

export const getDeletionsEmptyText = (hasKbFilter) =>
  hasKbFilter ? '\u6ca1\u6709\u7b26\u5408\u6761\u4ef6\u7684\u5220\u9664\u8bb0\u5f55' : '\u6682\u65e0\u5220\u9664\u8bb0\u5f55';

export const getDownloadsEmptyText = (hasKbFilter) =>
  hasKbFilter ? '\u6ca1\u6709\u7b26\u5408\u6761\u4ef6\u7684\u4e0b\u8f7d\u8bb0\u5f55' : '\u6682\u65e0\u4e0b\u8f7d\u8bb0\u5f55';

export const getVersionLoadingText = () => '\u52a0\u8f7d\u7248\u672c\u5386\u53f2\u4e2d...';

export const getVersionsEmptyText = () => '\u6682\u65e0\u7248\u672c\u5386\u53f2';

export const getEffectiveStatusLabel = (item, currentDocId) => {
  if (item.doc_id === currentDocId || item.is_current) {
    return '\u5f53\u524d\u751f\u6548';
  }
  return EFFECTIVE_STATUS_LABELS[item.effective_status] || item.effective_status || '\u5386\u53f2\u7248\u672c';
};
