import { useCallback, useRef } from 'react';
import { chatApi } from '../api';

export const useChatStream = ({
  selectedChatId,
  selectedSessionId,
  inputMessage,
  setInputMessage,
  messages,
  setMessages,
  setError,
  autoRenameSessionByFirstQuestion,
  normalizeForCompare,
  containsReasoningMarkers,
  stripThinkTags,
  saveSourcesForAssistantMessage,
  debugLogCitations,
  normalizeSource,
  refreshSessionMessages,
}) => {
  const assistantMessageRef = useRef('');
  const assistantSourcesRef = useRef([]);

  const isStreamDebugEnabled = useCallback(() => {
    if (process.env.NODE_ENV !== 'production') return true;
    try {
      return String(window?.localStorage?.getItem('RAGFLOWAUTH_DEBUG_CHAT_STREAM') || '') === '1';
    } catch {
      return false;
    }
  }, []);

  const previewText = useCallback((value, max = 200) => {
    const text = String(value || '');
    if (text.length <= max) return text;
    return `${text.slice(0, max)}...`;
  }, []);

  const logStream = useCallback(
    (level, message, payload = null) => {
      if (!isStreamDebugEnabled()) return;
      const writer = console?.[level] || console.log;
      if (payload === null || payload === undefined) {
        writer(`[Chat:stream] ${message}`);
      } else {
        writer(`[Chat:stream] ${message}`, payload);
      }
    },
    [isStreamDebugEnabled]
  );

  const readStreamFrame = useCallback(
    (payload) => {
      const frame = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : null;
      const data = frame?.data && typeof frame.data === 'object' && !Array.isArray(frame.data) ? frame.data : null;
      return {
        code: typeof frame?.code === 'number' ? frame.code : null,
        answer: typeof data?.answer === 'string' ? data.answer : '',
        sources: Array.isArray(data?.sources) ? data.sources : null,
        message: String(frame?.message || frame?.detail || '').trim(),
      };
    },
    []
  );

  const upsertAssistantMessage = useCallback(
    (content) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === 'assistant') {
          next[next.length - 1] = { ...last, role: 'assistant', content };
        } else {
          next.push({ role: 'assistant', content, sources: [] });
        }
        return next;
      });
    },
    [setMessages]
  );

  const upsertAssistantSources = useCallback(
    (sources) => {
      const list = Array.isArray(sources) ? sources : [];
      assistantSourcesRef.current = list;
      try {
        if (typeof debugLogCitations === 'function') {
          debugLogCitations(
            'sources received',
            list.map((s) => {
              const n = normalizeSource(s);
              return {
                raw_title: s?.filename || s?.title || s?.name || '',
                normalized_title: n.title,
                docId: n.docId,
                dataset: n.dataset,
              };
            })
          );
        }
      } catch {
        // ignore
      }
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === 'assistant') {
          next[next.length - 1] = { ...last, role: 'assistant', sources: list };
        } else {
          next.push({ role: 'assistant', content: '', sources: list });
        }
        return next;
      });
    },
    [debugLogCitations, normalizeSource, setMessages]
  );

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !selectedChatId || !selectedSessionId) return;
    const question = inputMessage.trim();
    const traceId = `chat_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    const sendStartedAt = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const userMessage = { role: 'user', content: question };
    const isFirstUserMessage = !(messages || []).some((m) => m?.role === 'user');

    logStream('info', 'send start', {
      traceId,
      selectedChatId,
      selectedSessionId,
      questionLen: question.length,
      isFirstUserMessage,
      currentMessageCount: Array.isArray(messages) ? messages.length : 0,
    });

    setMessages((prev) => [...prev, userMessage, { role: 'assistant', content: '', sources: [] }]);
    setInputMessage('');
    setError(null);

    try {
      if (isFirstUserMessage) {
        // Do not block first-turn completion on session rename.
        Promise.resolve(autoRenameSessionByFirstQuestion(question)).catch(() => {
          // Ignore rename failures/delay and keep chat streaming path responsive.
        });
      }

      const response = await chatApi.requestCompletionStream(selectedChatId, {
        question,
        sessionId: selectedSessionId,
        traceId,
      });

      logStream('info', 'send response received', {
        traceId,
        ok: response.ok,
        status: response.status,
        contentType: response.headers?.get?.('content-type') || '',
        transferEncoding: response.headers?.get?.('transfer-encoding') || '',
      });

      if (!response.ok) {
        throw new Error('send_failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let rawText = '';
      let consumedSseEvent = false;
      let receivedAnswerEvent = false;
      let readerChunkIndex = 0;
      let sseLineIndex = 0;
      assistantMessageRef.current = '';
      assistantSourcesRef.current = [];

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

          const incoming = frame.answer;
          if (incoming) {
            receivedAnswerEvent = true;
            if (incoming.toLowerCase().includes('<think')) {
              console.debug('[Chat:stream] think detected');
            }
            logStream('debug', 'answer event', {
              traceId,
              sseLineIndex,
              incomingLen: incoming.length,
              incomingPreview: previewText(incoming, 140),
            });

            const current = assistantMessageRef.current || '';
            const currentNorm = normalizeForCompare(current);
            const incomingNorm = normalizeForCompare(incoming);
            let next = '';

            if (current && incoming.startsWith(current)) {
              next = incoming;
            } else if (current && current.startsWith(incoming)) {
              next = current;
            } else if (current && incoming.includes(current) && incoming.length >= current.length) {
              next = incoming;
            }

            if (!next && (containsReasoningMarkers(incoming) || containsReasoningMarkers(current))) {
              if (incomingNorm.length >= currentNorm.length) {
                next = incoming;
              }
            }

            if (!next && currentNorm && incomingNorm && incomingNorm.length > currentNorm.length) {
              let prefixLen = 0;
              const max = Math.min(currentNorm.length, incomingNorm.length);
              for (let k = 0; k < max; k++) {
                if (currentNorm[k] !== incomingNorm[k]) break;
                prefixLen++;
              }
              const ratio = prefixLen / Math.max(1, currentNorm.length);
              if (ratio >= 0.8 || prefixLen >= 400) {
                next = incoming;
              }
            }

            if (next) {
              assistantMessageRef.current = next;
              upsertAssistantMessage(next);
              logStream('debug', 'assistant message updated', {
                traceId,
                sseLineIndex,
                nextLen: next.length,
                nextPreview: previewText(next, 140),
              });
              return;
            }

            if (incomingNorm === currentNorm) {
              next = current;
            } else if (incomingNorm.startsWith(currentNorm)) {
              next = incoming;
            } else if (incomingNorm.includes(currentNorm)) {
              next = incoming;
            } else if (currentNorm.startsWith(incomingNorm)) {
              next = current;
            } else if (currentNorm.includes(incomingNorm)) {
              next = current;
            } else {
              let overlap = 0;
              const max = Math.min(currentNorm.length, incomingNorm.length);
              for (let k = max; k > 0; k--) {
                if (currentNorm.endsWith(incomingNorm.slice(0, k))) {
                  overlap = k;
                  break;
                }
              }

              if (overlap > 0) {
                let rawOverlap = 0;
                const rawMax = Math.min(current.length, incoming.length);
                for (let k = rawMax; k > 0; k--) {
                  if (current.endsWith(incoming.slice(0, k))) {
                    rawOverlap = k;
                    break;
                  }
                }
                next = rawOverlap > 0 ? current + incoming.slice(rawOverlap) : incoming;
              } else {
                next = current + incoming;
              }
            }

            assistantMessageRef.current = next;
            upsertAssistantMessage(next);
            logStream('debug', 'assistant message merged', {
              traceId,
              sseLineIndex,
              nextLen: next.length,
              nextPreview: previewText(next, 140),
            });
          }

          if (frame.code !== 0) {
            const msg = frame.message || 'backend_error';
            setError(msg);
            upsertAssistantMessage(msg);
            logStream('warn', 'backend non-zero code', {
              traceId,
              sseLineIndex,
              code: frame.code,
              message: previewText(msg, 180),
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

      const visibleAssistantText = String(stripThinkTags(assistantMessageRef.current || '') || '').trim();
      if (!visibleAssistantText && !receivedAnswerEvent && !consumedSseEvent && typeof refreshSessionMessages === 'function') {
        try {
          logStream('warn', 'no answer parsed, refreshing session messages', {
            traceId,
            consumedSseEvent,
            receivedAnswerEvent,
            rawLen: String(rawText || '').length,
          });
          await Promise.resolve(refreshSessionMessages());
        } catch {
          logStream('warn', 'refresh session messages failed', { traceId });
        }
      }

      try {
        const finalText = stripThinkTags(assistantMessageRef.current || '');
        const finalSources = assistantSourcesRef.current || [];
        saveSourcesForAssistantMessage(selectedChatId, selectedSessionId, finalText, finalSources);
        const finishedAt = typeof performance !== 'undefined' ? performance.now() : Date.now();
        logStream('info', 'send finished', {
          traceId,
          durationMs: Math.max(0, Math.round(finishedAt - sendStartedAt)),
          readerChunkIndex,
          sseLineIndex,
          consumedSseEvent,
          receivedAnswerEvent,
          finalAnswerLen: finalText.length,
          finalSourcesCount: Array.isArray(finalSources) ? finalSources.length : 0,
        });
      } catch {
        logStream('warn', 'saveSourcesForAssistantMessage failed', { traceId });
      }
    } catch (err) {
      logStream('error', 'send failed', {
        traceId,
        message: String(err?.message || err || 'unknown_error'),
      });
      setError(err?.message || 'send_failed');
      setMessages((prev) => {
        const next = Array.isArray(prev) ? [...prev] : [];
        const last = next[next.length - 1];
        if (last?.role === 'assistant') next.pop();

        const hasCurrentUserQuestion = next.some(
          (msg) => msg?.role === 'user' && String(msg?.content || '') === question
        );
        if (!hasCurrentUserQuestion) {
          next.push({ role: 'user', content: question });
        }

        return next;
      });
    }
  }, [
    autoRenameSessionByFirstQuestion,
    containsReasoningMarkers,
    inputMessage,
    logStream,
    messages,
    normalizeForCompare,
    previewText,
    readStreamFrame,
    saveSourcesForAssistantMessage,
    refreshSessionMessages,
    selectedChatId,
    selectedSessionId,
    setError,
    setInputMessage,
    setMessages,
    stripThinkTags,
    upsertAssistantMessage,
    upsertAssistantSources,
  ]);

  return { sendMessage };
};
