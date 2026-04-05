import { act, renderHook, waitFor } from '@testing-library/react';
import { TextDecoder } from 'util';

import { chatApi } from '../api';
import { useChatStream } from './useChatStream';

jest.mock('../api', () => ({
  chatApi: {
    requestCompletionStream: jest.fn(),
  },
}));

if (typeof global.TextDecoder === 'undefined') {
  global.TextDecoder = TextDecoder;
}

function createStreamResponse(chunks) {
  const queue = (Array.isArray(chunks) ? chunks : []).map((item) => Uint8Array.from(Buffer.from(item, 'utf8')));
  let index = 0;

  return {
    ok: true,
    status: 200,
    headers: {
      get: jest.fn((name) => {
        if (String(name || '').toLowerCase() === 'content-type') return 'text/event-stream';
        return '';
      }),
    },
    body: {
      getReader() {
        return {
          read: jest.fn().mockImplementation(async () => {
            if (index >= queue.length) return { done: true, value: undefined };
            const value = queue[index];
            index += 1;
            return { done: false, value };
          }),
        };
      },
    },
  };
}

describe('useChatStream', () => {
  let consoleInfoSpy;
  let consoleDebugSpy;
  let consoleWarnSpy;
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleInfoSpy = jest.spyOn(console, 'info').mockImplementation(() => {});
    consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleInfoSpy.mockRestore();
    consoleDebugSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  it('consumes the explicit SSE answer/sources contract and persists the final assistant payload', async () => {
    let currentMessages = [];
    const setMessages = jest.fn((updater) => {
      currentMessages = typeof updater === 'function' ? updater(currentMessages) : updater;
    });
    const setInputMessage = jest.fn();
    const setError = jest.fn();
    const saveSourcesForAssistantMessage = jest.fn();
    const refreshSessionMessages = jest.fn().mockResolvedValue(true);

    chatApi.requestCompletionStream.mockResolvedValue(
      createStreamResponse([
        'data: {"code":0,"data":{"sources":[{"doc_id":"doc-1","dataset":"kb-1","filename":"Spec.pdf"}]}}\n\n',
        'data: {"code":0,"data":{"answer":"hello world"}}\n\n',
      ])
    );

    const { result } = renderHook(() =>
      useChatStream({
        selectedChatId: 'chat-1',
        selectedSessionId: 'session-1',
        inputMessage: 'hello',
        setInputMessage,
        messages: [],
        setMessages,
        setError,
        autoRenameSessionByFirstQuestion: jest.fn().mockResolvedValue(undefined),
        normalizeForCompare: (value) => String(value || ''),
        containsReasoningMarkers: () => false,
        stripThinkTags: (value) => String(value || ''),
        saveSourcesForAssistantMessage,
        debugLogCitations: jest.fn(),
        normalizeSource: (value) => value || {},
        refreshSessionMessages,
      })
    );

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(setInputMessage).toHaveBeenCalledWith('');
    expect(chatApi.requestCompletionStream).toHaveBeenCalledWith(
      'chat-1',
      expect.objectContaining({
        question: 'hello',
        sessionId: 'session-1',
      })
    );
    expect(currentMessages).toEqual([
      { role: 'user', content: 'hello' },
      {
        role: 'assistant',
        content: 'hello world',
        sources: [{ doc_id: 'doc-1', dataset: 'kb-1', filename: 'Spec.pdf' }],
      },
    ]);
    expect(saveSourcesForAssistantMessage).toHaveBeenCalledWith(
      'chat-1',
      'session-1',
      'hello world',
      [{ doc_id: 'doc-1', dataset: 'kb-1', filename: 'Spec.pdf' }]
    );
    expect(refreshSessionMessages).not.toHaveBeenCalled();
  });

  it('does not fall back to raw json bodies when the stream is not emitted as SSE lines', async () => {
    let currentMessages = [];
    const setMessages = jest.fn((updater) => {
      currentMessages = typeof updater === 'function' ? updater(currentMessages) : updater;
    });
    const refreshSessionMessages = jest.fn().mockResolvedValue(true);

    chatApi.requestCompletionStream.mockResolvedValue(
      createStreamResponse([
        '{"code":0,"data":{"answer":"raw body answer"}}',
      ])
    );

    const { result } = renderHook(() =>
      useChatStream({
        selectedChatId: 'chat-1',
        selectedSessionId: 'session-1',
        inputMessage: 'hello',
        setInputMessage: jest.fn(),
        messages: [],
        setMessages,
        setError: jest.fn(),
        autoRenameSessionByFirstQuestion: jest.fn().mockResolvedValue(undefined),
        normalizeForCompare: (value) => String(value || ''),
        containsReasoningMarkers: () => false,
        stripThinkTags: (value) => String(value || ''),
        saveSourcesForAssistantMessage: jest.fn(),
        debugLogCitations: jest.fn(),
        normalizeSource: (value) => value || {},
        refreshSessionMessages,
      })
    );

    await act(async () => {
      await result.current.sendMessage();
    });

    await waitFor(() => {
      expect(refreshSessionMessages).toHaveBeenCalledTimes(1);
    });
    expect(currentMessages).toEqual([
      { role: 'user', content: 'hello' },
      { role: 'assistant', content: '', sources: [] },
    ]);
  });
});
