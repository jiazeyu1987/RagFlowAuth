import { useCallback, useRef } from 'react';
import { chatApi } from '../api';
import {
  createStreamTraceId,
  previewStreamText,
  processCompletionStream,
  readCompletionStreamFrame,
  rollbackAssistantDraft,
  shouldRefreshSessionMessages,
} from './useChatStreamSupport';

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
    const traceId = createStreamTraceId();
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

      assistantMessageRef.current = '';
      assistantSourcesRef.current = [];
      const {
        rawText,
        consumedSseEvent,
        receivedAnswerEvent,
        readerChunkIndex,
        sseLineIndex,
      } = await processCompletionStream({
        response,
        traceId,
        logStream,
        previewText: previewStreamText,
        readStreamFrame: readCompletionStreamFrame,
        normalizeForCompare,
        containsReasoningMarkers,
        upsertAssistantMessage,
        upsertAssistantSources,
        setError,
        assistantMessageRef,
      });

      if (
        shouldRefreshSessionMessages({
          assistantMessage: assistantMessageRef.current,
          stripThinkTags,
          receivedAnswerEvent,
          consumedSseEvent,
        }) &&
        typeof refreshSessionMessages === 'function'
      ) {
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
      setMessages((prev) => rollbackAssistantDraft(prev, question));
    }
  }, [
    autoRenameSessionByFirstQuestion,
    containsReasoningMarkers,
    inputMessage,
    logStream,
    messages,
    normalizeForCompare,
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
