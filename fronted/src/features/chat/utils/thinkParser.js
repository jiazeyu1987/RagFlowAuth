export const normalizeForCompare = (value) => {
  return String(value ?? '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\u0000')
    .join('');
};

export const containsReasoningMarkers = (value) => {
  const s = String(value ?? '').toLowerCase();
  if (!s) return false;
  return (
    s.includes('<think') ||
    s.includes('</think>') ||
    s.includes('<begin_') ||
    s.includes('</begin_') ||
    s.includes('<tool') ||
    s.includes('</tool>')
  );
};

export const stripThinkTags = (value) => {
  const text = String(value ?? '');
  if (!text) return '';

  let out = text.replace(/<think\b[^>]*>[\s\S]*?<\/think>/gi, '');
  out = out.replace(/<think\b[^>]*>[\s\S]*$/gi, '');
  return out;
};

export const parseThinkSegments = (value) => {
  const text = String(value ?? '');
  if (!text) return [];

  const segs = [];
  let i = 0;

  while (i < text.length) {
    const open = text.toLowerCase().indexOf('<think', i);
    if (open === -1) {
      const tail = text.slice(i);
      if (tail) segs.push({ type: 'text', text: tail });
      break;
    }
    if (open > i) segs.push({ type: 'text', text: text.slice(i, open) });

    const openEnd = text.indexOf('>', open);
    if (openEnd === -1) {
      segs.push({ type: 'text', text: text.slice(open) });
      break;
    }

    const thinkStart = openEnd + 1;
    const close = text.toLowerCase().indexOf('</think>', thinkStart);
    if (close === -1) {
      const thinkTail = text.slice(thinkStart);
      if (thinkTail) segs.push({ type: 'think', text: thinkTail });
      break;
    }

    const thinkBody = text.slice(thinkStart, close);
    if (thinkBody) segs.push({ type: 'think', text: thinkBody });
    i = close + '</think>'.length;
  }

  return segs;
};
