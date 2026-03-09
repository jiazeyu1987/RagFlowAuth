export function getChunkDocumentInfo(chunk) {
  return {
    docId: chunk?.document_id || chunk?.doc_id || chunk?.docid,
    docName:
      chunk?.document_name ||
      chunk?.doc_name ||
      chunk?.docname ||
      chunk?.filename ||
      chunk?.document_keyword,
    datasetId: chunk?.dataset_id || chunk?.dataset || chunk?.kb_id,
  };
}

export function looksLikeMarkdownContent(content, docName) {
  const name = String(docName || '').toLowerCase().trim();
  if (name.endsWith('.md') || name.endsWith('.markdown')) return true;
  const text = String(content || '');
  if (!text) return false;
  if (/^#{1,6}\s+/m.test(text)) return true;
  if (/\n\|.*\|\n\|[-:| ]+\|/m.test(text) || /\|[-:| ]+\|/m.test(text)) return true;
  if (/^\s*[-*+]\s+/m.test(text) || /^\s*\d+\.\s+/m.test(text)) return true;
  return false;
}

export function highlightTextFallback(text, query) {
  const source = String(text || '');
  const needle = String(query || '').trim();
  if (!source || !needle) return source;
  const escapedQuery = needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escapedQuery})`, 'gi');
  return source.replace(regex, '<em>$1</em>');
}

export function normalizeInlinePipeKvTables(text) {
  const input = String(text ?? '');
  if (!input.includes('|')) return input;

  const makeTable = (pairs) => {
    const rows = pairs
      .filter((item) => item && typeof item.key === 'string' && typeof item.value === 'string')
      .map((item) => `| ${item.key} | ${item.value} |`);
    if (!rows.length) return '';
    return ['| 属性 | 值 |', '|---|---|', ...rows].join('\n');
  };

  const lines = input.split('\n');
  const output = [];

  for (const line of lines) {
    const raw = String(line ?? '');
    const trimmed = raw.trim();
    if (
      trimmed.startsWith('|') &&
      trimmed.includes('|') &&
      !trimmed.includes('|---') &&
      !trimmed.includes('<table') &&
      !trimmed.includes('</table>')
    ) {
      const tokens = trimmed
        .split('|')
        .map((token) => token.trim())
        .filter((token) => token.length > 0);

      if (tokens.length >= 3 && tokens.length % 2 === 1) tokens.push('');

      if (tokens.length >= 4 && tokens.length % 2 === 0) {
        const pairs = [];
        for (let i = 0; i < tokens.length; i += 2) {
          pairs.push({
            key: tokens[i],
            value: tokens[i + 1] ?? '',
          });
        }
        const table = makeTable(pairs);
        if (table) {
          output.push(table);
          continue;
        }
      }
    }
    output.push(raw);
  }

  return output.join('\n');
}
