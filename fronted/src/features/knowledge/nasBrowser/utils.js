export const ACTIVE_FOLDER_IMPORT_KEY = 'nas_active_folder_import_task';

export const PAGE_STYLE = {
  padding: '20px',
  width: '100%',
  boxSizing: 'border-box',
};

export const CARD_STYLE = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '16px',
};

export const BUTTON_STYLES = {
  neutral: {
    padding: '8px 12px',
    borderRadius: '10px',
    border: '1px solid #e5e7eb',
    background: '#fff',
    color: '#111827',
    cursor: 'pointer',
    fontWeight: 700,
  },
  primary: {
    padding: '8px 12px',
    borderRadius: '10px',
    border: '1px solid #dbeafe',
    background: '#eff6ff',
    color: '#1d4ed8',
    cursor: 'pointer',
    fontWeight: 700,
  },
  success: {
    padding: '8px 12px',
    borderRadius: '10px',
    border: '1px solid #bbf7d0',
    background: '#f0fdf4',
    color: '#15803d',
    cursor: 'pointer',
    fontWeight: 700,
  },
};

export const formatFileSize = (size) => {
  const value = Number(size || 0);
  if (!Number.isFinite(value) || value <= 0) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
};

export const formatTime = (value) => {
  if (!value) return '-';
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('zh-CN');
};

export const pathSegments = (path) => {
  const parts = String(path || '')
    .split('/')
    .map((part) => part.trim())
    .filter(Boolean);
  return [{ label: '根目录', path: '' }].concat(
    parts.map((part, index) => ({
      label: part,
      path: parts.slice(0, index + 1).join('/'),
    }))
  );
};

export const normalizeSkippedEntries = (items) => {
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => {
      if (typeof item === 'string') return { path: item, reason: 'skipped', detail: '' };
      if (!item || typeof item !== 'object') return null;
      return {
        path: String(item.path || ''),
        reason: String(item.reason || 'skipped'),
        detail: String(item.detail || ''),
      };
    })
    .filter((item) => item && item.path);
};

export const normalizeFailedEntries = (items) => {
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => {
      if (typeof item === 'string') return { path: item, reason: 'failed', detail: '' };
      if (!item || typeof item !== 'object') return null;
      return {
        path: String(item.path || ''),
        reason: String(item.reason || 'failed'),
        detail: String(item.detail || ''),
      };
    })
    .filter((item) => item && item.path);
};

export const formatImportReason = (reason, detail = '') => {
  const code = String(reason || '').trim().toLowerCase();
  if (code === 'unsupported_extension') return `Unsupported extension${detail ? ` (${detail})` : ''}`;
  if (code === 'ingestion_failed') return detail ? `Ingestion failed (${detail})` : 'Ingestion failed';
  if (detail) return `${reason}: ${detail}`;
  return reason || '-';
};

export const buildImportSummary = (result, noun) => {
  const skippedEntries = normalizeSkippedEntries(result?.skipped);
  const failedEntries = normalizeFailedEntries(result?.failed);
  const detailLines = [];
  skippedEntries.slice(0, 3).forEach((item) => detailLines.push(`Skipped: ${item.path} | ${formatImportReason(item.reason, item.detail)}`));
  failedEntries.slice(0, 3).forEach((item) => detailLines.push(`Failed: ${item.path} | ${formatImportReason(item.reason, item.detail)}`));
  return [
    `${noun} import completed`,
    '',
    `Imported: ${result.imported_count ?? 0}`,
    `Skipped: ${result.skipped_count ?? 0}`,
    `Failed: ${result.failed_count ?? 0}`,
    detailLines.length ? '' : null,
    ...detailLines,
  ]
    .filter(Boolean)
    .join('\n');
};

export const readStoredFolderImportTaskId = () => {
  try {
    const raw = window.localStorage.getItem(ACTIVE_FOLDER_IMPORT_KEY);
    if (!raw) return '';
    const parsed = JSON.parse(raw);
    return typeof parsed?.taskId === 'string' ? parsed.taskId : '';
  } catch {
    return '';
  }
};

export const writeStoredFolderImportTaskId = (taskId) => {
  try {
    if (!taskId) {
      window.localStorage.removeItem(ACTIVE_FOLDER_IMPORT_KEY);
      return;
    }
    window.localStorage.setItem(ACTIVE_FOLDER_IMPORT_KEY, JSON.stringify({ taskId }));
  } catch {
    // ignore storage failures
  }
};
