export function prettyJson(obj) {
  return JSON.stringify(obj ?? {}, null, 2);
}

export function parseJson(text) {
  try {
    const value = JSON.parse(text || '{}');
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return { ok: false, error: 'JSON must be an object' };
    }
    return { ok: true, value };
  } catch (error) {
    return { ok: false, error: `JSON parse failed: ${error?.message || String(error)}` };
  }
}
