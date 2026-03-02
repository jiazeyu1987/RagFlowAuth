export const isMarkdownFile = (filename) => {
  if (!filename) return false;
  const ext = String(filename).toLowerCase().split('.').pop();
  return ext === 'md' || ext === 'markdown';
};

export const isPlainTextFile = (filename) => {
  if (!filename) return false;
  const ext = String(filename).toLowerCase().split('.').pop();
  return ext === 'txt' || ext === 'ini' || ext === 'log';
};

export const isTextComparable = (filename) => isMarkdownFile(filename) || isPlainTextFile(filename);

export const countLines = (value) => {
  const text = String(value || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  if (!text) return 0;
  return text.split('\n').length;
};

export const formatDateTime = (timestampMs) => {
  if (!timestampMs) return '';
  return new Date(timestampMs).toLocaleString('zh-CN');
};
