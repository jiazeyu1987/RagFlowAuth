const DOWNLOAD_SUCCESS_STATUSES = new Set(['downloaded', 'downloaded_cached']);
const ACTIVE_SESSION_STATUSES = new Set(['running', 'stopping']);

export const clampLimit = (value, fallback = 10) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(1000, Math.max(1, Math.floor(n)));
};

export const isDownloadedItem = (item) => DOWNLOAD_SUCCESS_STATUSES.has(String(item?.status || ''));

export const getStatusChip = (item) => {
  if (item?.added_doc_id) return { text: '已添加', color: '#065f46', bg: '#d1fae5', border: '#a7f3d0' };
  if (item?.status === 'downloaded_cached') return { text: '已下载（历史）', color: '#374151', bg: '#f3f4f6', border: '#e5e7eb' };
  if (item?.status === 'downloaded') return { text: '已下载', color: '#1e3a8a', bg: '#dbeafe', border: '#bfdbfe' };
  return { text: '失败', color: '#991b1b', bg: '#fee2e2', border: '#fecaca' };
};

export const resolveItemSessionId = (item, activeSessionId = '') => String(item?.session_id || activeSessionId || '');

export const resolveHistoryKey = (historyList, currentKey = '') => {
  const list = Array.isArray(historyList) ? historyList : [];
  const normalizedCurrent = String(currentKey || '');
  if (normalizedCurrent && list.some((row) => String(row?.history_key || '') === normalizedCurrent)) {
    return normalizedCurrent;
  }
  return list.length ? String(list[0]?.history_key || '') : '';
};

export const isSessionActive = (status) => ACTIVE_SESSION_STATUSES.has(String(status || ''));
