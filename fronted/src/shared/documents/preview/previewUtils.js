export const isCsvFilename = (name) => String(name || '').toLowerCase().endsWith('.csv');

export const ONLYOFFICE_EXTENSIONS = new Set(['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']);

export const getFileExtensionLower = (name) => {
  const s = String(name || '').trim().toLowerCase();
  const idx = s.lastIndexOf('.');
  if (idx < 0) return '';
  return s.slice(idx);
};

export const base64ToBytes = (base64) => {
  const bin = atob(String(base64 || ''));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  return bytes;
};

export const nowMs = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

export const previewTrace = (step, meta = {}) => {
  // eslint-disable-next-line no-console
  console.info('[PreviewTrace][Modal]', step, meta);
};

const escapeHtml = (s) =>
  String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

export const detectDelimiter = (line) => {
  const candidates = [',', ';', '\t'];
  let best = ',';
  let bestCount = -1;
  for (const d of candidates) {
    const c = (line.match(new RegExp(`\\${d}`, 'g')) || []).length;
    if (c > bestCount) {
      bestCount = c;
      best = d;
    }
  }
  return best;
};

export const parseDelimited = (text, delimiter) => {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  const s = String(text ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    if (inQuotes) {
      if (ch === '"') {
        const next = s[i + 1];
        if (next === '"') {
          cell += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        cell += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
      continue;
    }

    if (ch === delimiter) {
      row.push(cell);
      cell = '';
      continue;
    }

    if (ch === '\n') {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
      continue;
    }

    cell += ch;
  }
  row.push(cell);
  rows.push(row);
  return rows;
};

export const rowsToHtmlTable = (rows) => {
  const safeRows = Array.isArray(rows) ? rows : [];
  const maxCols = safeRows.reduce((m, r) => Math.max(m, Array.isArray(r) ? r.length : 0), 0);
  const pad = (r) => {
    const out = Array.isArray(r) ? [...r] : [];
    while (out.length < maxCols) out.push('');
    return out;
  };
  const normalized = safeRows.map(pad);

  const body = normalized
    .map((r) => `<tr>${r.map((c) => `<td>${escapeHtml(c)}</td>`).join('')}</tr>`)
    .join('');
  return `<table><tbody>${body}</tbody></table>`;
};
