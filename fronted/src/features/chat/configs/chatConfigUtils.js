export const HIDDEN_CHAT_NAMES = new Set(['\u5927\u6a21\u578b', '\u5c0f\u6a21\u578b', '\u95ee\u9898\u6bd4\u5bf9']);
const HIDDEN_PARSED_FILE_FIELD_PATTERN = /parsed.*file|file.*parsed/i;

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
    return { ok: false, error: 'JSON parse failed: ' + (error?.message || String(error)) };
  }
}

export function getSelectedDatasetIdsFromChatJson(val) {
  const obj = val && typeof val === 'object' && !Array.isArray(val) ? val : {};
  const candidates = [obj.dataset_ids, obj.kb_ids, obj.datasetIds, obj.kbIds];
  for (const arr of candidates) {
    if (!Array.isArray(arr)) continue;
    const ids = arr.map((item) => String(item || '').trim()).filter(Boolean);
    if (ids.length) return ids;
  }

  const one = [obj.dataset_id, obj.datasetId, obj.kb_id, obj.kbId]
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  if (one.length) return one;

  if (Array.isArray(obj.datasets)) {
    const ids = [];
    for (const item of obj.datasets) {
      if (!item) continue;
      if (typeof item === 'string' || typeof item === 'number') {
        const id = String(item).trim();
        if (id) ids.push(id);
        continue;
      }
      if (typeof item === 'object') {
        const raw = item.id ?? item.dataset_id ?? item.kb_id ?? item.datasetId ?? item.kbId ?? '';
        const id = String(raw || '').trim();
        if (id) ids.push(id);
      }
    }
    return ids;
  }

  return [];
}

export function getDatasetIdsKeyForUpdate(val) {
  const obj = val && typeof val === 'object' && !Array.isArray(val) ? val : {};
  if (Array.isArray(obj.dataset_ids)) return 'dataset_ids';
  if (Array.isArray(obj.kb_ids)) return 'kb_ids';
  return 'dataset_ids';
}

export function sanitizeChatPayload(payload) {
  const body = payload && typeof payload === 'object' && !Array.isArray(payload) ? { ...payload } : {};

  delete body.id;
  delete body.chat_id;

  for (const key of ['tenant_id', 'create_time', 'update_time', 'status', 'token_num', 'document_count', 'chunk_count']) {
    delete body[key];
  }

  for (const key of Object.keys(body)) {
    if (key.endsWith('_task_id') || key.endsWith('_task_finish_at') || key.endsWith('_task_start_at')) delete body[key];
    if (HIDDEN_PARSED_FILE_FIELD_PATTERN.test(key)) delete body[key];
  }

  const derivedIds = getSelectedDatasetIdsFromChatJson(body);
  const hasExplicitIds = Array.isArray(body.dataset_ids) || Array.isArray(body.kb_ids);
  if (!hasExplicitIds && derivedIds.length) body.dataset_ids = derivedIds;

  delete body.datasets;
  return body;
}

