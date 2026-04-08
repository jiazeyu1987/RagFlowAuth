export const createStreamTraceId = ({
  now = () => Date.now(),
  random = () => Math.random(),
} = {}) => `chat_${now().toString(36)}_${random().toString(36).slice(2, 8)}`;

export const previewStreamText = (value, max = 200) => {
  const text = String(value || '');
  if (text.length <= max) return text;
  return `${text.slice(0, max)}...`;
};

export const readCompletionStreamFrame = (payload) => {
  const frame = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : null;
  const data =
    frame?.data && typeof frame.data === 'object' && !Array.isArray(frame.data) ? frame.data : null;

  return {
    code: typeof frame?.code === 'number' ? frame.code : null,
    answer: typeof data?.answer === 'string' ? data.answer : '',
    sources: Array.isArray(data?.sources) ? data.sources : null,
    message: String(frame?.message || frame?.detail || '').trim(),
  };
};

export const mergeAssistantAnswer = ({
  current,
  incoming,
  normalizeForCompare,
  containsReasoningMarkers,
}) => {
  const currentText = String(current || '');
  const incomingText = String(incoming || '');
  const currentNorm = normalizeForCompare(currentText);
  const incomingNorm = normalizeForCompare(incomingText);

  if (currentText && incomingText.startsWith(currentText)) {
    return incomingText;
  }
  if (currentText && currentText.startsWith(incomingText)) {
    return currentText;
  }
  if (currentText && incomingText.includes(currentText) && incomingText.length >= currentText.length) {
    return incomingText;
  }

  if (
    containsReasoningMarkers(incomingText) ||
    containsReasoningMarkers(currentText)
  ) {
    if (incomingNorm.length >= currentNorm.length) {
      return incomingText;
    }
  }

  if (currentNorm && incomingNorm && incomingNorm.length > currentNorm.length) {
    let prefixLen = 0;
    const max = Math.min(currentNorm.length, incomingNorm.length);
    for (let index = 0; index < max; index += 1) {
      if (currentNorm[index] !== incomingNorm[index]) break;
      prefixLen += 1;
    }
    const ratio = prefixLen / Math.max(1, currentNorm.length);
    if (ratio >= 0.8 || prefixLen >= 400) {
      return incomingText;
    }
  }

  if (incomingNorm === currentNorm) {
    return currentText;
  }
  if (incomingNorm.startsWith(currentNorm)) {
    return incomingText;
  }
  if (incomingNorm.includes(currentNorm)) {
    return incomingText;
  }
  if (currentNorm.startsWith(incomingNorm)) {
    return currentText;
  }
  if (currentNorm.includes(incomingNorm)) {
    return currentText;
  }

  let overlap = 0;
  const max = Math.min(currentNorm.length, incomingNorm.length);
  for (let index = max; index > 0; index -= 1) {
    if (currentNorm.endsWith(incomingNorm.slice(0, index))) {
      overlap = index;
      break;
    }
  }

  if (overlap > 0) {
    let rawOverlap = 0;
    const rawMax = Math.min(currentText.length, incomingText.length);
    for (let index = rawMax; index > 0; index -= 1) {
      if (currentText.endsWith(incomingText.slice(0, index))) {
        rawOverlap = index;
        break;
      }
    }
    return rawOverlap > 0 ? currentText + incomingText.slice(rawOverlap) : incomingText;
  }

  return currentText + incomingText;
};

export const shouldRefreshSessionMessages = ({
  assistantMessage,
  stripThinkTags,
  receivedAnswerEvent,
  consumedSseEvent,
}) => {
  const visibleAssistantText = String(stripThinkTags(assistantMessage || '') || '').trim();
  return !visibleAssistantText && !receivedAnswerEvent && !consumedSseEvent;
};

export const rollbackAssistantDraft = (previousMessages, question) => {
  const next = Array.isArray(previousMessages) ? [...previousMessages] : [];
  const last = next[next.length - 1];
  if (last?.role === 'assistant') {
    next.pop();
  }

  const hasCurrentUserQuestion = next.some(
    (message) => message?.role === 'user' && String(message?.content || '') === question
  );

  if (!hasCurrentUserQuestion) {
    next.push({ role: 'user', content: question });
  }

  return next;
};

export const processCompletionStream = async ({
  response,
  traceId,
  logStream,
  previewText = previewStreamText,
  readStreamFrame = readCompletionStreamFrame,
  normalizeForCompare,
  containsReasoningMarkers,
  upsertAssistantMessage,
  upsertAssistantSources,
  setError,
  assistantMessageRef,
}) => {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let rawText = '';
  let consumedSseEvent = false;
  let receivedAnswerEvent = false;
  let readerChunkIndex = 0;
  let sseLineIndex = 0;

  const processSseLine = (rawLine) => {
    sseLineIndex += 1;
    const line = String(rawLine ?? '')
      .replace(/^\uFEFF/, '')
      .trim();

    logStream('debug', 'sse line received', {
      traceId,
      sseLineIndex,
      rawLen: String(rawLine ?? '').length,
      linePreview: previewText(line, 180),
    });

    if (!line.startsWith('data:')) return;

    const dataStr = line.slice(5).trim();
    if (!dataStr || dataStr === '[DONE]') return;

    try {
      consumedSseEvent = true;
      const data = JSON.parse(dataStr);

      logStream('debug', 'sse json parsed', {
        traceId,
        sseLineIndex,
        code: data?.code,
        dataType: typeof data?.data,
        topKeys: data && typeof data === 'object' ? Object.keys(data).slice(0, 8) : [],
      });

      const frame = readStreamFrame(data);
      if (frame.code === null) {
        logStream('warn', 'invalid sse payload ignored', {
          traceId,
          sseLineIndex,
          dataPreview: previewText(dataStr, 180),
        });
        return;
      }

      if (Array.isArray(frame.sources)) {
        upsertAssistantSources(frame.sources);
        logStream('debug', 'sources event', {
          traceId,
          sseLineIndex,
          sourcesCount: frame.sources.length,
        });
      }

      if (frame.answer) {
        receivedAnswerEvent = true;
        if (frame.answer.toLowerCase().includes('<think')) {
          console.debug('[Chat:stream] think detected');
        }

        const nextMessage = mergeAssistantAnswer({
          current: assistantMessageRef.current || '',
          incoming: frame.answer,
          normalizeForCompare,
          containsReasoningMarkers,
        });

        assistantMessageRef.current = nextMessage;
        upsertAssistantMessage(nextMessage);
        logStream('debug', 'assistant message updated', {
          traceId,
          sseLineIndex,
          nextLen: nextMessage.length,
          nextPreview: previewText(nextMessage, 140),
        });
      }

      if (frame.code !== 0) {
        const message = frame.message || 'backend_error';
        setError(message);
        upsertAssistantMessage(message);
        logStream('warn', 'backend non-zero code', {
          traceId,
          sseLineIndex,
          code: frame.code,
          message: previewText(message, 180),
        });
      }
    } catch {
      logStream('warn', 'malformed sse chunk ignored', {
        traceId,
        sseLineIndex,
        dataPreview: previewText(dataStr, 180),
      });
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    readerChunkIndex += 1;
    const decoded = decoder.decode(value, { stream: true });
    rawText += decoded;
    buffer += decoded;
    logStream('debug', 'reader chunk', {
      traceId,
      readerChunkIndex,
      byteLength: value?.byteLength || 0,
      decodedLen: decoded.length,
      decodedPreview: previewText(decoded, 180),
    });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      processSseLine(line);
    }
  }

  if (buffer) {
    processSseLine(buffer);
  }

  return {
    rawText,
    consumedSseEvent,
    receivedAnswerEvent,
    readerChunkIndex,
    sseLineIndex,
  };
};
