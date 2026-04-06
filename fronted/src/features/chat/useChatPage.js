import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '../../hooks/useAuth';
import { useEscapeClose } from '../../shared/hooks/useEscapeClose';
import { ensureTablePreviewStyles } from '../../shared/preview/tablePreviewStyles';
import { DOCUMENT_SOURCE, documentsApi } from '../documents/api';
import { useChatSessions } from './hooks/useChatSessions';
import { useChatStream } from './hooks/useChatStream';
import {
  normalizeSource,
  restoreSourcesIntoMessages,
  saveSourcesForAssistantMessage,
} from './utils/citationStore';
import {
  containsReasoningMarkers,
  normalizeForCompare,
  stripThinkTags,
} from './utils/thinkParser';

const MOBILE_BREAKPOINT = 768;

export default function useChatPage() {
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;

  const [inputMessage, setInputMessage] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [citationHover, setCitationHover] = useState(null);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => {
      setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const closePreview = useCallback(() => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  }, []);

  const debugChatCitations = useCallback(() => {
    try {
      return String(window?.localStorage?.getItem('RAGFLOWAUTH_DEBUG_CHAT_CITATIONS') || '') === '1';
    } catch {
      return false;
    }
  }, []);

  const debugLogCitations = useCallback(
    (...args) => {
      if (!debugChatCitations()) return;
      console.debug('[Chat:Citations]', ...args);
    },
    [debugChatCitations]
  );

  const restoreSourcesForSession = useCallback(
    (chatId, sessionId, messageList) =>
      restoreSourcesIntoMessages(chatId, sessionId, messageList, stripThinkTags),
    []
  );

  const {
    chats,
    selectedChatId,
    sessions,
    selectedSessionId,
    messages,
    loading,
    error,
    deleteConfirm,
    renameDialog,
    actions,
  } = useChatSessions({
    restoreSourcesIntoMessages: restoreSourcesForSession,
  });

  const { sendMessage } = useChatStream({
    selectedChatId,
    selectedSessionId,
    inputMessage,
    setInputMessage,
    messages,
    setMessages: actions.setMessages,
    setError: actions.setError,
    autoRenameSessionByFirstQuestion: actions.autoRenameSessionByFirstQuestion,
    normalizeForCompare,
    containsReasoningMarkers,
    stripThinkTags,
    saveSourcesForAssistantMessage: (chatId, sessionId, content, sources) =>
      saveSourcesForAssistantMessage(chatId, sessionId, content, sources, debugLogCitations),
    debugLogCitations,
    normalizeSource,
    refreshSessionMessages: actions.refreshCurrentSessionMessages,
  });

  useEscapeClose(deleteConfirm.show, actions.closeDeleteConfirm);
  useEscapeClose(renameDialog.show, actions.closeRenameDialog);
  useEscapeClose(previewOpen, closePreview);

  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages]);

  const openSourcePreview = useCallback(
    (rawSource) => {
      const source = normalizeSource(rawSource);
      if (!source.docId || !source.dataset) return;
      debugLogCitations('preview open', {
        before_title: source.title,
        docId: source.docId,
        dataset: source.dataset,
      });
      setPreviewTarget({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId: source.docId,
        datasetName: source.dataset,
        filename: source.title,
      });
      setPreviewOpen(true);
    },
    [debugLogCitations]
  );

  const downloadSource = useCallback(
    async (rawSource) => {
      const source = normalizeSource(rawSource);
      if (!source.docId || !source.dataset) return;
      if (!canDownloadFiles) throw new Error('no_download_permission');
      await documentsApi.downloadToBrowser({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId: source.docId,
        datasetName: source.dataset,
        filename: source.title,
      });
    },
    [canDownloadFiles]
  );

  const onCitationClick = useCallback((event, { id, chunk }) => {
    const rect = event?.currentTarget?.getBoundingClientRect?.();
    const x = rect ? rect.left + rect.width / 2 : event?.clientX ?? 0;
    const y = rect ? rect.top : event?.clientY ?? 0;
    console.debug('[Chat:CitationPopup] open', { id, chunkLen: String(chunk || '').length, x, y });
    setCitationHover({
      id,
      chunk: String(chunk || '').trim() || '(未获取到 chunk 内容)',
      x,
      y,
    });
  }, []);

  const onCitationPopupLeave = useCallback(() => {
    console.debug('[Chat:CitationPopup] close');
    setCitationHover(null);
  }, []);

  const handleComposerKeyPress = useCallback(
    (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (selectedChatId && selectedSessionId) {
          sendMessage();
        }
      }
    },
    [selectedChatId, selectedSessionId, sendMessage]
  );

  const openRenameDialog = useCallback(
    (session) => {
      actions.setRenameDialog({ show: true, sessionId: session.id, value: session.name || '' });
    },
    [actions]
  );

  const openDeleteDialog = useCallback(
    (session) => {
      actions.setDeleteConfirm({
        show: true,
        sessionId: session.id,
        sessionName: session.name || session.id,
      });
    },
    [actions]
  );

  const setRenameDialogValue = useCallback(
    (value) => {
      actions.setRenameDialog((previous) => ({ ...previous, value }));
    },
    [actions]
  );

  return {
    canDownloadFiles,
    inputMessage,
    previewOpen,
    previewTarget,
    citationHover,
    isMobile,
    messagesEndRef,
    chats,
    selectedChatId,
    sessions,
    selectedSessionId,
    messages,
    loading,
    error,
    deleteConfirm,
    renameDialog,
    setInputMessage,
    setSelectedChatId: actions.setSelectedChatId,
    createSession: actions.createSession,
    selectSession: actions.selectSession,
    setError: actions.setError,
    confirmDeleteSession: actions.confirmDeleteSession,
    closeDeleteConfirm: actions.closeDeleteConfirm,
    confirmRenameSession: actions.confirmRenameSession,
    closeRenameDialog: actions.closeRenameDialog,
    closePreview,
    sendMessage,
    openSourcePreview,
    downloadSource,
    onCitationClick,
    onCitationPopupLeave,
    handleComposerKeyPress,
    openRenameDialog,
    openDeleteDialog,
    setRenameDialogValue,
  };
}
