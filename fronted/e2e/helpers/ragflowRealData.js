// @ts-check

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_CHAT_NAME = '\u5c55\u5385\u804a\u5929';
const DEFAULT_CHAT_PROMPTS = [
  '\u4ecb\u7ecd\u4e00\u4e0b\u5bfc\u4e1d',
  '\u538b\u529b\u6cf5\u5728 PCI \u624b\u672f\u91cc\u7684\u4f5c\u7528\u662f\u4ec0\u4e48',
];
const DEFAULT_SEARCH_TERMS = [
  '\u5bfc\u4e1d',
  '\u538b\u529b\u6cf5',
  '\u795e\u7ecf\u4ecb\u5165',
  '\u6b62\u8840\u9600',
  '\u9b54\u828b\u5fae\u7403',
];

function parseCsvEnv(raw, fallback) {
  const text = String(raw || '').trim();
  if (!text) return [...fallback];
  const items = text
    .split(',')
    .map((s) => String(s || '').trim())
    .filter(Boolean);
  return items.length ? items : [...fallback];
}

function parseIntEnv(raw, fallback) {
  const n = Number.parseInt(String(raw || ''), 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function uniqueTerms(values) {
  const out = [];
  const seen = new Set();
  for (const raw of values || []) {
    const term = String(raw || '').trim();
    if (!term) continue;
    if (seen.has(term)) continue;
    seen.add(term);
    out.push(term);
  }
  return out;
}

function parseCsvOnly(raw) {
  return uniqueTerms(
    String(raw || '')
      .split(',')
      .map((s) => String(s || '').trim())
      .filter(Boolean)
  );
}

function parseLineTerms(rawText) {
  return uniqueTerms(
    String(rawText || '')
      .split(/\r?\n/g)
      .map((line) => line.replace(/#.*/g, '').trim())
      .filter(Boolean)
  );
}

function loadTermsFromFile(filePath) {
  const p = String(filePath || '').trim();
  if (!p) return [];
  try {
    if (!fs.existsSync(p)) return [];
    const text = fs.readFileSync(p, 'utf8');
    return parseLineTerms(text);
  } catch {
    return [];
  }
}

function readStrictFlag() {
  return String(process.env.E2E_REQUIRE_REAL_FLOW || '').trim() === '1';
}

function normalizeChatName(rawName) {
  return String(rawName || '')
    .trim()
    .replace(/^\[+|\]+$/g, '')
    .trim();
}

function getRealDataConfig() {
  const envSearchTerms = parseCsvOnly(process.env.E2E_REAL_SEARCH_TERMS);
  const defaultTermsFile = path.resolve(__dirname, '..', 'fixtures', 'ragflow_real_search_terms.txt');
  const termsFile = String(process.env.E2E_REAL_SEARCH_TERMS_FILE || defaultTermsFile).trim() || defaultTermsFile;
  const fileSearchTerms = loadTermsFromFile(termsFile);
  const resolvedSearchTerms = uniqueTerms(
    envSearchTerms.length ? envSearchTerms : fileSearchTerms.length ? fileSearchTerms : DEFAULT_SEARCH_TERMS
  );

  return {
    strict: readStrictFlag(),
    chatName: String(process.env.E2E_REAL_CHAT_NAME || DEFAULT_CHAT_NAME).trim() || DEFAULT_CHAT_NAME,
    chatPrompts: parseCsvEnv(process.env.E2E_REAL_CHAT_PROMPTS, DEFAULT_CHAT_PROMPTS),
    searchTerms: resolvedSearchTerms,
    searchTermsFile: termsFile,
    maxTerms: parseIntEnv(process.env.E2E_REAL_MAX_TERMS, 3),
    minHitTerms: parseIntEnv(process.env.E2E_REAL_MIN_HIT_TERMS, 2),
    minAnswerChars: parseIntEnv(process.env.E2E_REAL_MIN_ANSWER_CHARS, 8),
  };
}

async function listMyChats(api, headers) {
  const resp = await api.get('/api/chats/my', { headers });
  if (!resp.ok()) {
    return { ok: false, reason: `GET /api/chats/my failed (${resp.status()})`, chats: [] };
  }
  const payload = await resp.json();
  const chats = Array.isArray(payload?.chats) ? payload.chats : [];
  return { ok: true, reason: '', chats };
}

async function findChatByName(api, headers, expectedName) {
  const listed = await listMyChats(api, headers);
  if (!listed.ok) return { ok: false, reason: listed.reason, chat: null };
  const target = listed.chats.find((chat) => normalizeChatName(chat?.name) === normalizeChatName(expectedName));
  if (!target) return { ok: false, reason: `chat not found: ${expectedName}`, chat: null };
  return { ok: true, reason: '', chat: target };
}

async function listDatasetIds(api, headers) {
  const resp = await api.get('/api/datasets', { headers });
  if (!resp.ok()) {
    return { ok: false, reason: `GET /api/datasets failed (${resp.status()})`, datasetIds: [] };
  }
  const payload = await resp.json();
  const datasets = Array.isArray(payload?.datasets) ? payload.datasets : [];
  const datasetIds = datasets.map((x) => x?.id).filter(Boolean);
  if (!datasetIds.length) {
    return { ok: false, reason: 'no dataset available for search', datasetIds: [] };
  }
  return { ok: true, reason: '', datasetIds };
}

async function searchChunks(api, headers, datasetIds, term) {
  const resp = await api.post('/api/search', {
    headers,
    data: {
      question: String(term || '').trim(),
      dataset_ids: datasetIds,
      page: 1,
      page_size: 30,
      similarity_threshold: 0.2,
      top_k: 30,
      keyword: false,
      highlight: false,
    },
  });
  if (!resp.ok()) {
    return { ok: false, reason: `/api/search failed (${resp.status()}) for term=${term}`, chunks: [], response: null };
  }
  const payload = await resp.json();
  const chunks = Array.isArray(payload?.chunks) ? payload.chunks : [];
  return { ok: true, reason: '', chunks, response: payload };
}

async function pickSearchTermsWithHits(api, headers, datasetIds, candidateTerms, maxTerms) {
  const chosen = [];
  for (const rawTerm of candidateTerms) {
    const term = String(rawTerm || '').trim();
    if (!term) continue;
    const result = await searchChunks(api, headers, datasetIds, term);
    if (!result.ok) continue;
    if (result.chunks.length <= 0) continue;
    chosen.push({ term, hitCount: result.chunks.length });
    if (chosen.length >= maxTerms) break;
  }
  return chosen;
}

module.exports = {
  getRealDataConfig,
  normalizeChatName,
  findChatByName,
  listDatasetIds,
  searchChunks,
  pickSearchTermsWithHits,
};
