const CHINESE_TEXT_PATTERN = /[\u3400-\u9fff]/;

export const normalizeDisplayError = (message, fallback = '操作失败') => {
  const text = typeof message === 'string' ? message.trim() : String(message || '').trim();
  return CHINESE_TEXT_PATTERN.test(text) ? text : fallback;
};
