export const getFileExtensionLower = (name = '') => {
  const idx = name.lastIndexOf('.');
  if (idx < 0) return '';
  return name.slice(idx).toLowerCase();
};

export const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes)) return '-';
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(2)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(2)} MB`;
};

export const getDisplayPath = (file) => String(file?.webkitRelativePath || file?.name || '');

export const getFileUniqueKey = (file) => `${getDisplayPath(file)}__${file?.size || 0}__${file?.lastModified || 0}`;

export const normalizeExtension = (value = '') => {
  let next = String(value || '').trim().toLowerCase();
  if (!next) return '';
  if (!next.startsWith('.')) next = `.${next}`;
  return next;
};
