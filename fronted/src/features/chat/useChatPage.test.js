import { act, renderHook } from '@testing-library/react';

import { useAuth } from '../../hooks/useAuth';
import { documentsApi } from '../documents/api';
import useChatPage from './useChatPage';
import { useChatSessions } from './hooks/useChatSessions';
import { useChatStream } from './hooks/useChatStream';

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../documents/api', () => ({
  DOCUMENT_SOURCE: {
    RAGFLOW: 'ragflow',
  },
  documentsApi: {
    downloadToBrowser: jest.fn(),
  },
}));

jest.mock('./hooks/useChatSessions', () => ({
  useChatSessions: jest.fn(),
}));

jest.mock('./hooks/useChatStream', () => ({
  useChatStream: jest.fn(),
}));

const createChatSessionState = (overrides = {}) => ({
  chats: [{ id: 'chat-1', name: '质量助手' }],
  selectedChatId: 'chat-1',
  sessions: [{ id: 'session-1', name: '会话一', messages: [] }],
  selectedSessionId: 'session-1',
  messages: [],
  loading: false,
  error: '',
  deleteConfirm: { show: false, sessionId: null, sessionName: '' },
  renameDialog: { show: false, sessionId: null, value: '' },
  actions: {
    setMessages: jest.fn(),
    setError: jest.fn(),
    autoRenameSessionByFirstQuestion: jest.fn(),
    refreshCurrentSessionMessages: jest.fn(),
    closeDeleteConfirm: jest.fn(),
    closeRenameDialog: jest.fn(),
    confirmDeleteSession: jest.fn(),
    confirmRenameSession: jest.fn(),
    setDeleteConfirm: jest.fn(),
    setRenameDialog: jest.fn(),
    setSelectedChatId: jest.fn(),
    createSession: jest.fn(),
    selectSession: jest.fn(),
  },
  ...overrides,
});

describe('useChatPage', () => {
  let consoleDebugSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation(() => {});
    useAuth.mockReturnValue({
      canDownload: () => true,
    });
    useChatSessions.mockReturnValue(createChatSessionState());
    useChatStream.mockReturnValue({
      sendMessage: jest.fn(),
    });
  });

  afterEach(() => {
    consoleDebugSpy.mockRestore();
  });

  it('opens a normalized source preview and downloads through the documents api', async () => {
    const { result } = renderHook(() => useChatPage());
    const rawSource = {
      doc_id: 'doc-1',
      dataset: 'kb-1',
      filename: 'Spec.pdf',
    };

    act(() => {
      result.current.openSourcePreview(rawSource);
    });

    expect(result.current.previewOpen).toBe(true);
    expect(result.current.previewTarget).toEqual({
      source: 'ragflow',
      docId: 'doc-1',
      datasetName: 'kb-1',
      filename: 'Spec.pdf',
    });

    await act(async () => {
      await result.current.downloadSource(rawSource);
    });

    expect(documentsApi.downloadToBrowser).toHaveBeenCalledWith({
      source: 'ragflow',
      docId: 'doc-1',
      datasetName: 'kb-1',
      filename: 'Spec.pdf',
    });
  });

  it('sends on Enter and manages citation hover state in the page hook', () => {
    const sendMessage = jest.fn();
    useChatStream.mockReturnValue({
      sendMessage,
    });

    const { result } = renderHook(() => useChatPage());
    const preventDefault = jest.fn();

    act(() => {
      result.current.handleComposerKeyPress({
        key: 'Enter',
        shiftKey: false,
        preventDefault,
      });
    });

    expect(preventDefault).toHaveBeenCalledTimes(1);
    expect(sendMessage).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.onCitationClick(
        {
          currentTarget: {
            getBoundingClientRect: () => ({ left: 20, top: 30, width: 40 }),
          },
        },
        { id: 2, chunk: '引用片段' }
      );
    });

    expect(result.current.citationHover).toEqual({
      id: 2,
      chunk: '引用片段',
      x: 40,
      y: 30,
    });

    act(() => {
      result.current.onCitationPopupLeave();
    });

    expect(result.current.citationHover).toBe(null);
  });
});
