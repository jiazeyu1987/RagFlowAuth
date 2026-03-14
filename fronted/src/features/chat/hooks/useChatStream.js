import { useCallback, useRef } from 'react';
import { httpClient } from '../../../shared/http/httpClient';

const SAFETY_STAGE_META = [
  { key: 'classify', label: '分级' },
  { key: 'desensitize', label: '脱敏' },
  { key: 'intercept', label: '拦截' },
];

const SAFETY_STAGE_KEYWORD_MAP = {
  classify: ['classify', 'classification', 'classify_text', 'grade', 'sensitivity', '分级', '敏感分级'],
  desensitize: ['desensitize', 'desensitization', 'mask', 'redact', 'sanitize', '脱敏', '去标识'],
  intercept: ['intercept', 'block', 'blocked', 'gate', 'policy', 'deny', 'reject', '拦截', '阻断', '拒绝'],
};

const SAFETY_STATUS_KEYWORD_MAP = {
  pending: ['pending', 'wait', 'queued', '等待'],
  running: ['running', 'processing', 'in_progress', 'working', '执行中', '处理中'],
  success: ['success', 'ok', 'pass', 'allowed', 'done', 'completed', '通过', '放行', '完成'],
  failed: ['failed', 'error', 'blocked', 'reject', 'denied', 'intercepted', '失败', '拦截', '拒绝'],
  skipped: ['skip', 'skipped', 'ignored', '跳过'],
};

const createInitialSafetyFlow = () => ({
  visible: true,
  fromBackend: false,
  finished: false,
  summary: '正在分级...',
  stages: SAFETY_STAGE_META.map((item, index) => ({
    ...item,
    status: index === 0 ? 'running' : 'pending',
    detail: '',
  })),
});

const normalizeSafetyToken = (value) =>
  String(value || '')
    .trim()
    .toLowerCase();

const normalizeSafetyStageKey = (value) => {
  const token = normalizeSafetyToken(value);
  if (!token) return '';
  for (const [stageKey, keywords] of Object.entries(SAFETY_STAGE_KEYWORD_MAP)) {
    if (keywords.some((keyword) => token.includes(keyword))) return stageKey;
  }
  return '';
};

const normalizeSafetyStatus = (value) => {
  const token = normalizeSafetyToken(value);
  if (!token) return '';
  for (const [statusKey, keywords] of Object.entries(SAFETY_STATUS_KEYWORD_MAP)) {
    if (keywords.some((keyword) => token.includes(keyword))) return statusKey;
  }
  return '';
};

const cloneSafetyFlow = (flow) => ({
  ...flow,
  stages: Array.isArray(flow?.stages) ? flow.stages.map((stage) => ({ ...stage })) : [],
});

const getSafetyStageIndex = (stageKey) => SAFETY_STAGE_META.findIndex((stage) => stage.key === stageKey);

const getRunningSafetyStageIndex = (flow) =>
  flow?.stages?.findIndex((stage) => stage?.status === 'running') ?? -1;

const getPendingSafetyStageIndex = (flow) =>
  flow?.stages?.findIndex((stage) => stage?.status === 'pending') ?? -1;

const isPendingOrRunning = (status) => status === 'pending' || status === 'running';

const markStagesBeforeIndexAsSuccess = (flow, stageIndex) => {
  for (let i = 0; i < stageIndex; i += 1) {
    if (!flow.stages[i]) continue;
    if (flow.stages[i].status === 'pending' || flow.stages[i].status === 'running') {
      flow.stages[i].status = 'success';
    }
  }
};

const extractSafetyPayload = (payload) => {
  const candidates = [
    payload?.data?.safety,
    payload?.data?.security,
    payload?.safety,
    payload?.security,
    payload?.data,
    payload,
  ];

  for (const raw of candidates) {
    if (!raw || typeof raw !== 'object') continue;

    const stageRaw = raw.security_stage ?? raw.safety_stage ?? raw.stage ?? raw.step ?? raw.phase ?? raw.node;
    const statusRaw = raw.security_status ?? raw.safety_status ?? raw.status ?? raw.state ?? raw.result;
    const summary = String(raw.summary ?? raw.security_summary ?? raw.safety_summary ?? '').trim();
    const detail = String(raw.detail ?? raw.message ?? raw.reason ?? '').trim();
    const stage = normalizeSafetyStageKey(stageRaw);
    const status = normalizeSafetyStatus(statusRaw);

    const merged = `${String(stageRaw || '')} ${String(statusRaw || '')} ${summary} ${detail}`;
    const blocked = Boolean(raw.blocked ?? raw.intercepted ?? raw.rejected)
      || /blocked|reject|denied|intercept|拦截|拒绝|阻断/i.test(merged);
    const done = Boolean(raw.done ?? raw.finished ?? raw.complete ?? raw.completed)
      || /done|finish|completed|通过|放行|完成/i.test(merged);

    const hasSafetyContext = /safety|security|分级|脱敏|拦截|敏感/i.test(merged);
    if (stage || status || hasSafetyContext || blocked || done) {
      return {
        stage,
        status,
        summary,
        detail,
        blocked,
        done,
      };
    }
  }
  return null;
};

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
  const assistantSafetyRef = useRef(createInitialSafetyFlow());
  const fallbackSafetyProgressRef = useRef({ parsed: false, answered: false });

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

  const pickText = useCallback((value) => {
    const walk = (node) => {
      if (typeof node === 'string') return node.trim();
      if (Array.isArray(node)) {
        for (const item of node) {
          const got = walk(item);
          if (got) return got;
        }
        return '';
      }
      if (!node || typeof node !== 'object') return '';

      for (const key of ['answer', 'content', 'text', 'response']) {
        const got = walk(node?.[key]);
        if (got) return got;
      }
      for (const key of ['message', 'delta', 'data', 'output', 'result', 'choices', 'parts']) {
        const got = walk(node?.[key]);
        if (got) return got;
      }
      return '';
    };
    return walk(value);
  }, []);

  const extractIncomingAnswer = useCallback(
    (payload) => {
      const data = payload && typeof payload === 'object' ? payload.data : null;
      const candidates = [data, payload];
      for (const value of candidates) {
        const text = pickText(value);
        if (text) return text;
      }
      return '';
    },
    [pickText]
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

  const mutateAssistantSafetyFlow = useCallback(
    (mutator) => {
      const base = cloneSafetyFlow(assistantSafetyRef.current || createInitialSafetyFlow());
      const next = typeof mutator === 'function' ? mutator(base) || base : base;
      const safeFlow = cloneSafetyFlow(next);
      assistantSafetyRef.current = safeFlow;

      setMessages((prev) => {
        const list = Array.isArray(prev) ? [...prev] : [];
        const last = list[list.length - 1];
        if (last?.role === 'assistant') {
          list[list.length - 1] = { ...last, role: 'assistant', safetyFlow: cloneSafetyFlow(safeFlow) };
        } else {
          list.push({
            role: 'assistant',
            content: '',
            sources: [],
            safetyFlow: cloneSafetyFlow(safeFlow),
          });
        }
        return list;
      });
      return safeFlow;
    },
    [setMessages]
  );

  const applyBackendSafetyPayload = useCallback(
    (safetyPayload) => {
      if (!safetyPayload) return;
      mutateAssistantSafetyFlow((flow) => {
        flow.visible = true;
        flow.fromBackend = true;

        const stageIndex = getSafetyStageIndex(safetyPayload.stage);
        if (stageIndex >= 0) {
          markStagesBeforeIndexAsSuccess(flow, stageIndex);
          const targetStage = flow.stages[stageIndex];
          if (safetyPayload.detail) {
            targetStage.detail = safetyPayload.detail;
          }
          if (safetyPayload.status) {
            targetStage.status = safetyPayload.status;
          } else if (safetyPayload.blocked) {
            targetStage.status = 'failed';
          } else if (safetyPayload.done) {
            targetStage.status = 'success';
          } else if (targetStage.status === 'pending') {
            targetStage.status = 'running';
          }
        } else if (safetyPayload.detail) {
          const runningIndex = getRunningSafetyStageIndex(flow);
          if (runningIndex >= 0) {
            flow.stages[runningIndex].detail = safetyPayload.detail;
          }
        }

        const shouldBlock = safetyPayload.blocked || safetyPayload.status === 'failed';
        if (shouldBlock) {
          const fallbackIndex = getRunningSafetyStageIndex(flow);
          const failIndex = stageIndex >= 0 ? stageIndex : fallbackIndex >= 0 ? fallbackIndex : flow.stages.length - 1;
          if (failIndex >= 0) {
            markStagesBeforeIndexAsSuccess(flow, failIndex);
            if (flow.stages[failIndex]) {
              flow.stages[failIndex].status = 'failed';
              if (safetyPayload.detail && !flow.stages[failIndex].detail) {
                flow.stages[failIndex].detail = safetyPayload.detail;
              }
            }
            for (let i = failIndex + 1; i < flow.stages.length; i += 1) {
              if (isPendingOrRunning(flow.stages[i]?.status)) {
                flow.stages[i].status = 'skipped';
              }
            }
          }
          flow.finished = true;
          flow.summary = safetyPayload.summary || '命中安全策略，已拦截回复';
          return flow;
        }

        const shouldFinish =
          safetyPayload.done || (safetyPayload.status === 'success' && !safetyPayload.stage && !safetyPayload.detail);
        if (shouldFinish) {
          for (let i = 0; i < flow.stages.length; i += 1) {
            if (isPendingOrRunning(flow.stages[i]?.status)) {
              flow.stages[i].status = 'success';
            }
          }
          flow.finished = true;
          flow.summary = safetyPayload.summary || '安全流程完成，已放行回复';
          return flow;
        }

        if (safetyPayload.summary) {
          flow.summary = safetyPayload.summary;
          return flow;
        }

        if (stageIndex >= 0) {
          const stage = flow.stages[stageIndex];
          if (stage?.status === 'running') {
            flow.summary = `正在${stage.label}...`;
          } else {
            const pendingIndex = getPendingSafetyStageIndex(flow);
            if (pendingIndex >= 0) {
              flow.summary = `正在${flow.stages[pendingIndex].label}...`;
            }
          }
        }
        return flow;
      });
    },
    [mutateAssistantSafetyFlow]
  );

  const advanceFallbackSafetyFlow = useCallback(
    (phase) => {
      mutateAssistantSafetyFlow((flow) => {
        if (flow.fromBackend) return flow;

        const classifyIndex = getSafetyStageIndex('classify');
        const desensitizeIndex = getSafetyStageIndex('desensitize');
        const interceptIndex = getSafetyStageIndex('intercept');

        if (phase === 'parsed') {
          if (classifyIndex >= 0 && isPendingOrRunning(flow.stages[classifyIndex]?.status)) {
            flow.stages[classifyIndex].status = 'success';
          }
          if (desensitizeIndex >= 0 && flow.stages[desensitizeIndex]?.status === 'pending') {
            flow.stages[desensitizeIndex].status = 'running';
            flow.summary = `正在${flow.stages[desensitizeIndex].label}...`;
          }
          return flow;
        }

        if (phase === 'answered') {
          if (desensitizeIndex >= 0 && isPendingOrRunning(flow.stages[desensitizeIndex]?.status)) {
            markStagesBeforeIndexAsSuccess(flow, desensitizeIndex);
            flow.stages[desensitizeIndex].status = 'success';
          }
          if (interceptIndex >= 0 && flow.stages[interceptIndex]?.status === 'pending') {
            flow.stages[interceptIndex].status = 'running';
            flow.summary = `正在${flow.stages[interceptIndex].label}...`;
          }
          return flow;
        }

        return flow;
      });
    },
    [mutateAssistantSafetyFlow]
  );

  const finalizeSafetyFlow = useCallback(
    (mode) => {
      mutateAssistantSafetyFlow((flow) => {
        if (mode === 'error') {
          const runningIndex = getRunningSafetyStageIndex(flow);
          const pendingIndex = getPendingSafetyStageIndex(flow);
          const failIndex = runningIndex >= 0 ? runningIndex : pendingIndex;
          if (failIndex >= 0) {
            markStagesBeforeIndexAsSuccess(flow, failIndex);
            flow.stages[failIndex].status = 'failed';
            if (!flow.stages[failIndex].detail) {
              flow.stages[failIndex].detail = '流程异常中断';
            }
            for (let i = failIndex + 1; i < flow.stages.length; i += 1) {
              if (isPendingOrRunning(flow.stages[i]?.status)) {
                flow.stages[i].status = 'skipped';
              }
            }
          }
          flow.finished = true;
          flow.summary = '安全流程异常中断';
          return flow;
        }

        if (!flow.finished) {
          const failedIndex = flow.stages.findIndex((stage) => stage?.status === 'failed');
          if (failedIndex >= 0) {
            for (let i = failedIndex + 1; i < flow.stages.length; i += 1) {
              if (isPendingOrRunning(flow.stages[i]?.status)) {
                flow.stages[i].status = 'skipped';
              }
            }
            flow.summary = flow.summary || '命中安全策略，已拦截回复';
          } else {
            for (let i = 0; i < flow.stages.length; i += 1) {
              if (isPendingOrRunning(flow.stages[i]?.status)) {
                flow.stages[i].status = 'success';
              }
            }
            if (!flow.summary || /^正在/.test(flow.summary)) {
              flow.summary = '安全流程完成，已放行回复';
            }
          }
          flow.finished = true;
        }
        return flow;
      });
    },
    [mutateAssistantSafetyFlow]
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

    assistantSafetyRef.current = createInitialSafetyFlow();
    fallbackSafetyProgressRef.current = { parsed: false, answered: false };
    setMessages((prev) => [
      ...prev,
      userMessage,
      { role: 'assistant', content: '', sources: [], safetyFlow: cloneSafetyFlow(assistantSafetyRef.current) },
    ]);
    setInputMessage('');
    setError(null);

    try {
      if (isFirstUserMessage) {
        // Do not block first-turn completion on session rename.
        Promise.resolve(autoRenameSessionByFirstQuestion(question)).catch(() => {
          // Ignore rename failures/delay and keep chat streaming path responsive.
        });
      }

      const response = await httpClient.request(`/api/chats/${selectedChatId}/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Chat-Trace-Id': traceId },
        body: JSON.stringify({ question, stream: true, session_id: selectedSessionId }),
      });

      logStream('info', 'send response received', {
        traceId,
        ok: response.ok,
        status: response.status,
        contentType: response.headers?.get?.('content-type') || '',
        transferEncoding: response.headers?.get?.('transfer-encoding') || '',
      });

      if (!response.ok) {
        throw new Error('发送失败');
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
      assistantSafetyRef.current = createInitialSafetyFlow();
      fallbackSafetyProgressRef.current = { parsed: false, answered: false };

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

          const safetyPayload = extractSafetyPayload(data);
          if (safetyPayload) {
            applyBackendSafetyPayload(safetyPayload);
            logStream('debug', 'safety event', {
              traceId,
              sseLineIndex,
              stage: safetyPayload.stage || '',
              status: safetyPayload.status || '',
              blocked: !!safetyPayload.blocked,
              done: !!safetyPayload.done,
              summary: previewText(safetyPayload.summary || '', 120),
            });
          }

          if (!assistantSafetyRef.current?.fromBackend && !fallbackSafetyProgressRef.current.parsed) {
            fallbackSafetyProgressRef.current.parsed = true;
            advanceFallbackSafetyFlow('parsed');
          }

          if (data?.code === 0 && data?.data && Array.isArray(data.data.sources)) {
            upsertAssistantSources(data.data.sources);
            logStream('debug', 'sources event', {
              traceId,
              sseLineIndex,
              sourcesCount: data.data.sources.length,
            });
          }

          const incoming = extractIncomingAnswer(data);
          if (incoming) {
            receivedAnswerEvent = true;
            if (!assistantSafetyRef.current?.fromBackend && !fallbackSafetyProgressRef.current.answered) {
              fallbackSafetyProgressRef.current.answered = true;
              advanceFallbackSafetyFlow('answered');
            }
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

          if (typeof data?.code === 'number' && data.code !== 0) {
            const msg = String(data?.message || data?.detail || '后端异常');
            setError(msg);
            upsertAssistantMessage(msg);
            finalizeSafetyFlow('error');
            logStream('warn', 'backend non-zero code', {
              traceId,
              sseLineIndex,
              code: data.code,
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

      // Compatibility fallback: some proxies downgrade stream response to one JSON body.
      if (!consumedSseEvent && !assistantMessageRef.current) {
        try {
          const rawTrimmed = String(rawText || '').trim();
          if (rawTrimmed) {
            const payload = JSON.parse(rawTrimmed);
            const safetyPayload = extractSafetyPayload(payload);
            if (safetyPayload) {
              applyBackendSafetyPayload(safetyPayload);
            }
            if (!assistantSafetyRef.current?.fromBackend && !fallbackSafetyProgressRef.current.parsed) {
              fallbackSafetyProgressRef.current.parsed = true;
              advanceFallbackSafetyFlow('parsed');
            }
            const incoming = extractIncomingAnswer(payload);
            if (incoming) {
              if (!assistantSafetyRef.current?.fromBackend && !fallbackSafetyProgressRef.current.answered) {
                fallbackSafetyProgressRef.current.answered = true;
                advanceFallbackSafetyFlow('answered');
              }
              assistantMessageRef.current = incoming;
              upsertAssistantMessage(incoming);
            }
            const maybeSources = payload?.data?.sources;
            if (Array.isArray(maybeSources)) {
              upsertAssistantSources(maybeSources);
            }
            logStream('info', 'json-body fallback used', {
              traceId,
              rawLen: rawTrimmed.length,
              fallbackAnswerLen: String(assistantMessageRef.current || '').length,
            });
          }
        } catch {
          logStream('warn', 'json-body fallback failed', {
            traceId,
            rawPreview: previewText(rawText, 180),
          });
        }
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

      finalizeSafetyFlow('done');

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
      finalizeSafetyFlow('error');
      setError(err?.message || '发送失败');
      setMessages((prev) => {
        const next = Array.isArray(prev) ? [...prev] : [];
        const hasCurrentUserQuestion = next.some(
          (msg) => msg?.role === 'user' && String(msg?.content || '') === question
        );
        if (!hasCurrentUserQuestion) {
          next.push({ role: 'user', content: question });
        }

        const last = next[next.length - 1];
        const failedSafetyFlow = cloneSafetyFlow(assistantSafetyRef.current || createInitialSafetyFlow());
        if (last?.role === 'assistant') {
          next[next.length - 1] = {
            ...last,
            role: 'assistant',
            content: String(last?.content || '请求失败，请稍后重试'),
            safetyFlow: failedSafetyFlow,
          };
        } else {
          next.push({
            role: 'assistant',
            content: '请求失败，请稍后重试',
            sources: [],
            safetyFlow: failedSafetyFlow,
          });
        }

        return next;
      });
    }
  }, [
    advanceFallbackSafetyFlow,
    applyBackendSafetyPayload,
    autoRenameSessionByFirstQuestion,
    containsReasoningMarkers,
    extractIncomingAnswer,
    finalizeSafetyFlow,
    inputMessage,
    logStream,
    messages,
    normalizeForCompare,
    previewText,
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
