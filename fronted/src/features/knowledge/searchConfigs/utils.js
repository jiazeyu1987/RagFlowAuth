export function prettyJson(obj) {
  return JSON.stringify(obj ?? {}, null, 2);
}

export function parseJson(text) {
  try {
    const value = JSON.parse(text || '{}');
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return { ok: false, error: 'JSON 必须是对象' };
    }
    return { ok: true, value };
  } catch (error) {
    return { ok: false, error: `JSON 解析失败：${error?.message || String(error)}` };
  }
}
